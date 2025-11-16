"""
Osmosis-Structure-0.6B wrapper for post-hoc structured extraction.

Enables two-pass workflow:
1. LLM generates free-form reasoning (Claude)
2. Osmosis extracts valid Pydantic models

Proven: +284% accuracy improvement on complex reasoning tasks (AIME benchmark).

Supports both local (Ollama) and API (Inference.net) deployments.
"""

from typing import Type, TypeVar, Optional, Dict, Any
from pydantic import BaseModel
import httpx
import json
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)

# Check if ollama library is available
try:
    from ollama import chat as ollama_chat
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    logger.warning("ollama library not installed. Install with: pip install ollama")


class OsmosisExtractor:
    """
    Unified wrapper for Osmosis-Structure-0.6B extraction.

    Supports both local (Ollama) and API deployments with automatic fallback.

    Two-Pass Workflow:
        1. LLM (Claude) reasons freely without structure constraints
        2. Osmosis extracts valid Pydantic models from reasoning text

    Benefits:
        - +284% accuracy on complex reasoning (AIME benchmark)
        - Separation of concerns: reasoning vs. formatting
        - Guaranteed valid Pydantic models
        - Only +6.7% cost increase (API) or 0% (Ollama local)
    """

    def __init__(
        self,
        mode: str = "ollama",
        api_key: Optional[str] = None,
        endpoint: Optional[str] = None,
        model_name: str = "Osmosis/Osmosis-Structure-0.6B",
        timeout: int = 30,
        enable_fallback: bool = True,
    ):
        """
        Initialize Osmosis extractor.

        Args:
            mode: Deployment mode ("ollama" for local, "api" for hosted)
            api_key: API key for inference.net (required if mode="api")
            endpoint: API endpoint (default: https://api.inference.net/v1/osmosis)
            model_name: Osmosis model name
            timeout: Request timeout in seconds
            enable_fallback: Enable fallback to direct Pydantic parsing if Osmosis fails
        """
        self.mode = mode
        self.api_key = api_key or os.getenv("OSMOSIS_API_KEY")
        self.endpoint = endpoint or os.getenv(
            "OSMOSIS_ENDPOINT",
            "https://api.inference.net/v1/osmosis"
        )
        self.model_name = model_name
        self.timeout = timeout
        self.enable_fallback = enable_fallback

        # Ollama local endpoint
        self.ollama_endpoint = os.getenv(
            "OLLAMA_ENDPOINT",
            "http://localhost:11434/api/generate"
        )

        self.client = httpx.AsyncClient(timeout=timeout)

        logger.info(
            f"Initialized OsmosisExtractor in {mode} mode "
            f"(fallback={'enabled' if enable_fallback else 'disabled'})"
        )

    async def extract(
        self,
        text: str,
        schema: Type[T],
        extraction_prompt: Optional[str] = None,
    ) -> T:
        """
        Extract structured output from free-form text.

        Two-pass workflow:
        1. LLM generated 'text' (free reasoning, no constraints)
        2. Osmosis extracts valid Pydantic model from text

        Args:
            text: Free-form text from LLM (Claude analysis)
            schema: Target Pydantic model class
            extraction_prompt: Optional custom extraction instruction

        Returns:
            Validated instance of schema class

        Raises:
            ValueError: If extraction fails and fallback disabled
        """
        logger.debug(f"Extracting {schema.__name__} from {len(text)} chars of text")

        # Convert Pydantic model to JSON schema
        json_schema = schema.model_json_schema()

        # Build extraction prompt
        if extraction_prompt is None:
            extraction_prompt = self._build_default_prompt(json_schema, schema.__name__)

        # Route to appropriate backend
        try:
            if self.mode == "ollama":
                extracted_json = await self._extract_ollama(text, extraction_prompt, schema)
            elif self.mode == "api":
                extracted_json = await self._extract_api(text, extraction_prompt)
            else:
                raise ValueError(f"Unknown mode: {self.mode}")

            # Validate and parse with Pydantic
            validated = schema.model_validate(extracted_json)
            logger.info(f"✓ Successfully extracted {schema.__name__}")
            return validated

        except Exception as e:
            logger.warning(f"Osmosis extraction failed: {e}")

            if self.enable_fallback:
                logger.info("Attempting fallback to direct Pydantic parsing")
                return await self._fallback_parse(text, schema)
            else:
                raise ValueError(f"Osmosis extraction failed: {e}")

    def _build_default_prompt(self, json_schema: dict, schema_name: str) -> str:
        """Build default extraction prompt from JSON schema."""
        schema_str = json.dumps(json_schema, indent=2)

        return f"""Extract structured information from the text and format it according to this JSON schema for {schema_name}:

{schema_str}

Instructions:
- Extract ALL relevant information from the text
- Ensure output STRICTLY follows the schema
- Use null for missing optional fields
- Preserve exact values where possible
- Be comprehensive - don't omit information

Output ONLY valid JSON matching the schema. No additional text or explanation."""

    async def _extract_ollama(self, text: str, extraction_prompt: str, schema: Type[T]) -> dict:
        """Extract using local Ollama deployment with ollama library."""
        if not OLLAMA_AVAILABLE:
            raise ValueError(
                "ollama library not installed. Install with: pip install ollama"
            )

        try:
            logger.debug(f"Calling Ollama with model {self.model_name}")

            # Get JSON schema for the format parameter
            json_schema = schema.model_json_schema()

            # Use ollama.chat() with proper format parameter
            # This ensures Osmosis returns valid JSON matching the schema
            response = ollama_chat(
                messages=[
                    {
                        "role": "system",
                        "content": f"You are a helpful assistant that understands and translates text to JSON format according to the following schema. {json_schema}"
                    },
                    {
                        "role": "user",
                        "content": text,
                    }
                ],
                model=self.model_name,
                format=json_schema,
            )

            # Extract JSON content from response
            content = response.message.content
            logger.debug(f"Osmosis returned: {content[:200]}...")

            # Parse and return JSON
            extracted_json = json.loads(content)
            return extracted_json

        except json.JSONDecodeError as e:
            raise ValueError(f"Ollama returned invalid JSON: {e}\nContent: {content}")
        except Exception as e:
            raise ValueError(f"Ollama extraction failed: {e}")

    async def _extract_api(self, text: str, extraction_prompt: str) -> dict:
        """Extract using hosted API deployment."""
        if not self.api_key:
            raise ValueError(
                "API key required for API mode. "
                "Set OSMOSIS_API_KEY environment variable or pass api_key parameter."
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model_name,
            "text": text,
            "prompt": extraction_prompt,
            "temperature": 0.1,
        }

        try:
            logger.debug(f"Calling API at {self.endpoint}")
            response = await self.client.post(
                self.endpoint,
                headers=headers,
                json=payload,
            )
            response.raise_for_status()

            result = response.json()
            extracted = result.get("extracted", {})

            if not extracted:
                raise ValueError("API returned empty extraction")

            return extracted

        except httpx.HTTPStatusError as e:
            raise ValueError(f"API HTTP error {e.response.status_code}: {e}")
        except Exception as e:
            raise ValueError(f"API extraction failed: {e}")

    async def _fallback_parse(self, text: str, schema: Type[T]) -> T:
        """
        Fallback: Use Claude's structured output for extraction.

        When Osmosis fails (e.g., model not configured properly),
        fall back to Claude Haiku for structured extraction.

        Args:
            text: Text to parse
            schema: Pydantic model class

        Returns:
            Validated schema instance

        Raises:
            ValueError: If parsing fails
        """
        logger.info("Using fallback: Claude structured output")

        try:
            # Try pattern matching first (fast)
            json_candidates = []

            # Pattern 1: JSON in code block
            if "```json" in text:
                start = text.find("```json") + 7
                end = text.find("```", start)
                if end != -1:
                    json_candidates.append(text[start:end].strip())

            # Pattern 2: JSON in curly braces
            if "{" in text and "}" in text:
                start = text.find("{")
                end = text.rfind("}") + 1
                json_candidates.append(text[start:end])

            # Try each candidate
            for i, candidate in enumerate(json_candidates):
                try:
                    parsed = json.loads(candidate)
                    validated = schema.model_validate(parsed)
                    logger.info(f"✓ Fallback succeeded with pattern {i+1}")
                    return validated
                except Exception:
                    continue

            # Pattern matching failed, use Claude for extraction
            logger.info("Pattern matching failed, using Claude for extraction")

            from langchain_google_genai import ChatGoogleGenerativeAI

            # Initialize Claude Haiku (cost-effective)
            llm = ChatGoogleGenerativeAI(
                model="claude-3-haiku-20240307",
                temperature=0.0,
            )

            # Use with_structured_output for reliable extraction
            structured_llm = llm.with_structured_output(schema)

            # Extract with Claude
            extraction_prompt = f"""Extract structured information from the following text.
Return a valid {schema.__name__} object with all fields properly populated.

Text to extract from:
{text}

Extract all relevant information accurately."""

            result = structured_llm.invoke(extraction_prompt)
            logger.info(f"✓ Claude fallback succeeded for {schema.__name__}")
            return result

        except Exception as e:
            raise ValueError(f"Fallback extraction failed: {e}")

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Example usage
async def example():
    """Example: Extract reflection insights from Claude's analysis."""

    # Mock schema for demonstration
    from pydantic import Field

    class ExampleInsight(BaseModel):
        """Example insight model."""
        content: str = Field(description="Insight description")
        category: str = Field(description="helpful, harmful, or neutral")
        confidence: float = Field(description="Confidence score 0.0-1.0")

    class ExampleInsightList(BaseModel):
        """List of insights."""
        insights: list[ExampleInsight]

    # Initialize extractor (Ollama mode for zero cost)
    extractor = OsmosisExtractor(mode="ollama")

    # Claude's free-form analysis (no structure constraints)
    analysis = """
    After analyzing the execution, I identified several key insights:

    1. The delegate_to_researcher() call was extremely helpful because it provided
       comprehensive source material with exact citations. This enabled the writer
       to create a well-referenced document. I'm very confident about this pattern.

    2. However, the data_scientist was not given enough context about the research
       question, which led to statistical tests on irrelevant variables. This was
       harmful and wasted computational resources. I'm moderately confident this
       should be avoided.

    3. The file approval timeout of 300 seconds seems too long for simple edits.
       Consider reducing to 60 seconds for operations under 100 lines. This is
       a neutral observation worth testing.
    """

    try:
        # Extract structured insights (two-pass workflow)
        insights = await extractor.extract(
            text=analysis,
            schema=ExampleInsightList,
        )

        print(f"\n✓ Extracted {len(insights.insights)} structured insights:\n")
        for i, insight in enumerate(insights.insights, 1):
            print(f"{i}. [{insight.category}] {insight.content}")
            print(f"   Confidence: {insight.confidence:.2f}\n")

    except Exception as e:
        print(f"✗ Extraction failed: {e}")

    finally:
        await extractor.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(example())
