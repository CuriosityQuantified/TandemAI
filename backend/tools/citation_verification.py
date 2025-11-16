"""
Citation Verification Tools

Tools for caching Tavily search results and verifying citations against cached data.
This eliminates the need for additional API calls during verification.

Key Features:
- Automatic caching of Tavily results to PostgreSQL
- Fast quote verification using database lookups
- Session-based tracking for research workflows
- Full-text search support for finding quotes
"""

import os
import re
from typing import Dict, List, Optional
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
from langchain_core.tools import tool
from langchain_tavily import TavilySearch


def get_postgres_connection():
    """Get PostgreSQL connection for Tavily cache."""
    postgres_uri = os.getenv("POSTGRES_URI")
    if not postgres_uri:
        raise ValueError("POSTGRES_URI environment variable not set")
    return psycopg2.connect(postgres_uri)


def normalize_text(text: str) -> str:
    """
    Normalize text for comparison.

    - Collapses whitespace
    - Converts to lowercase
    - Removes extra spaces

    Args:
        text: Text to normalize

    Returns:
        Normalized text
    """
    return ' '.join(text.split()).lower()


@tool
def tavily_search_cached(query: str, session_id: str, search_depth: str = "advanced") -> dict:
    """
    Search the web using Tavily and cache results for citation verification.

    All results are automatically saved to PostgreSQL database with the session_id.
    This enables later verification of quotes without additional API calls.

    Args:
        query: Search query string
        session_id: Research session identifier (typically the plan_id)
        search_depth: "basic" or "advanced" (default: advanced)

    Returns:
        Dict containing search results from Tavily

    Example:
        result = tavily_search_cached(
            query="quantum error correction 2025",
            session_id="plan_20251115_213543"
        )
    """
    # Get Tavily API key
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        return {
            "error": "TAVILY_API_KEY not found in environment variables",
            "results": []
        }

    # Perform Tavily search using LangChain v1.0+ integration
    try:
        # Initialize TavilySearch with max_results parameter
        tavily_tool = TavilySearch(
            max_results=5,
            search_depth=search_depth,
            include_raw_content=True,  # Important for verification
            api_key=tavily_api_key
        )

        # Execute search - returns a list of result dicts
        search_results = tavily_tool.invoke(query)

        # Convert to expected format
        results = {
            "results": search_results if isinstance(search_results, list) else [],
            "query": query
        }
    except Exception as e:
        return {
            "error": f"Tavily search failed: {str(e)}",
            "results": []
        }

    # Cache results in database
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor()

        for result in results.get("results", []):
            cursor.execute("""
                INSERT INTO tavily_search_cache
                    (session_id, query, search_depth, url, title, content, raw_content, score, published_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (session_id, url)
                DO UPDATE SET
                    content = EXCLUDED.content,
                    raw_content = EXCLUDED.raw_content,
                    score = EXCLUDED.score,
                    search_timestamp = NOW()
            """, (
                session_id,
                query,
                search_depth,
                result.get("url", ""),
                result.get("title", ""),
                result.get("content", ""),
                result.get("raw_content", ""),
                result.get("score", 0.0),
                result.get("published_date", "")
            ))

        conn.commit()
        cursor.close()
        conn.close()

        # Add cache confirmation to results
        results["_cached"] = True
        results["_session_id"] = session_id
        results["_cached_count"] = len(results.get("results", []))

    except Exception as e:
        # Log error but don't fail the search
        results["_cache_error"] = str(e)
        results["_cached"] = False

    return results


@tool
def verify_citations(response_text: str, session_id: str) -> Dict:
    """
    Verify all quoted text against cached Tavily results.

    Checks that every quote in the response can be found in the Tavily search
    results cached during research. NO external API calls are made.

    Citation Format Expected:
        Inline: "exact quote" [Source, URL, Date] [#]
        Source List: [#] "exact quote" - Source - URL - Date

    Args:
        response_text: Complete response with inline citations and source list
        session_id: Research session identifier (must match tavily_search_cached calls)

    Returns:
        {
            "all_verified": bool,              # True if all quotes verified
            "total_citations": int,             # Total citations found
            "verified_count": int,              # Number verified
            "failed_citations": [               # List of failures
                {
                    "ref_num": int,
                    "quote": str,
                    "url": str,
                    "reason": str
                }
            ],
            "verification_details": [           # Detailed results
                {
                    "ref_num": int,
                    "status": "verified" | "failed",
                    "found_in": "content" | "raw_content" | None
                }
            ]
        }

    Example:
        result = verify_citations(
            response_text="## Research Findings...",
            session_id="plan_20251115_213543"
        )

        if not result["all_verified"]:
            print("Failed citations:", result["failed_citations"])
    """
    # Extract citations from source list
    # Pattern: [#] "quote" - Source - URL - Date
    pattern = r'\[(\d+)\]\s*"([^"]+)"\s*-\s*([^-]+)\s*-\s*(https?://[^\s]+)'
    citations = re.findall(pattern, response_text)

    results = {
        "all_verified": True,
        "total_citations": len(citations),
        "verified_count": 0,
        "failed_citations": [],
        "verification_details": []
    }

    if len(citations) == 0:
        results["all_verified"] = False
        results["failed_citations"].append({
            "ref_num": 0,
            "quote": "",
            "url": "",
            "reason": "No citations found in response. Expected format: [#] \"quote\" - Source - URL - Date"
        })
        return results

    # Connect to database
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        for ref_num, quote, source, url in citations:
            # Normalize quote for comparison (collapse whitespace, lowercase)
            quote_normalized = normalize_text(quote)

            # Query cached Tavily results for this URL
            cursor.execute("""
                SELECT content, raw_content, title, score
                FROM tavily_search_cache
                WHERE session_id = %s AND url = %s
                LIMIT 1
            """, (session_id, url))

            result = cursor.fetchone()

            if not result:
                # URL not in cache - wasn't from Tavily search
                results["all_verified"] = False
                results["failed_citations"].append({
                    "ref_num": int(ref_num),
                    "quote": quote[:100] + "..." if len(quote) > 100 else quote,
                    "url": url,
                    "reason": "URL not found in Tavily search results for this session. Only cite sources from your tavily_search results."
                })
                results["verification_details"].append({
                    "ref_num": int(ref_num),
                    "status": "failed",
                    "found_in": None
                })
                continue

            # Search in content (try both content and raw_content)
            content_normalized = normalize_text(result["content"] or "")
            raw_normalized = normalize_text(result["raw_content"] or "")

            found_in_content = quote_normalized in content_normalized
            found_in_raw = quote_normalized in raw_normalized

            if found_in_content or found_in_raw:
                results["verified_count"] += 1
                results["verification_details"].append({
                    "ref_num": int(ref_num),
                    "status": "verified",
                    "found_in": "content" if found_in_content else "raw_content",
                    "relevance_score": float(result["score"]) if result["score"] else 0.0
                })
            else:
                results["all_verified"] = False
                results["failed_citations"].append({
                    "ref_num": int(ref_num),
                    "quote": quote[:100] + "..." if len(quote) > 100 else quote,
                    "url": url,
                    "source_title": result["title"],
                    "reason": "Quote not found in Tavily search result content. The quote must be an EXACT excerpt from the source.",
                    "suggestion": "Re-read the Tavily result and extract the exact text. Do not paraphrase or modify quotes."
                })
                results["verification_details"].append({
                    "ref_num": int(ref_num),
                    "status": "failed",
                    "found_in": None
                })

        cursor.close()
        conn.close()

    except Exception as e:
        results["all_verified"] = False
        results["failed_citations"].append({
            "ref_num": 0,
            "quote": "",
            "url": "",
            "reason": f"Database error during verification: {str(e)}"
        })

    return results


@tool
def get_cached_source_content(url: str, session_id: str) -> Dict:
    """
    Retrieve cached content for a specific URL from this session.

    Useful when you need to re-read a source to find the correct quote.

    Args:
        url: The source URL
        session_id: Research session identifier

    Returns:
        {
            "found": bool,
            "url": str,
            "title": str,
            "content": str,
            "score": float
        }
    """
    try:
        conn = get_postgres_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT url, title, content, raw_content, score, published_date
            FROM tavily_search_cache
            WHERE session_id = %s AND url = %s
            LIMIT 1
        """, (session_id, url))

        result = cursor.fetchone()

        cursor.close()
        conn.close()

        if result:
            return {
                "found": True,
                "url": result["url"],
                "title": result["title"],
                "content": result["content"],
                "raw_content": result["raw_content"],
                "score": float(result["score"]) if result["score"] else 0.0,
                "published_date": result["published_date"]
            }
        else:
            return {
                "found": False,
                "error": f"URL not found in session {session_id}. Did you search for this source with tavily_search_cached?"
            }

    except Exception as e:
        return {
            "found": False,
            "error": f"Database error: {str(e)}"
        }


# Export tools for use in agent configurations
__all__ = [
    "tavily_search_cached",
    "verify_citations",
    "get_cached_source_content"
]
