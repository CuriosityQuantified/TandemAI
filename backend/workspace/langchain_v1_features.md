# LangChain v1.0 Features Research

## Overview

LangChain v1.0 represents the first major stable release of the LangChain framework, marking a commitment to stability with no breaking changes until v2.0[^1]. The release focuses on streamlining the framework to core agent-building capabilities while introducing powerful new abstractions for production use[^1].

## Core Improvements

### 1. **New `create_agent` API**

LangChain v1.0 introduces a new standard way to build agents through the `create_agent` function, replacing the previous `create_react_agent` from LangGraph[^2][^3]. This provides a cleaner, more powerful API that simplifies agent development and serves as the foundation for building AI applications[^3].

### 2. **Standard Content Blocks**

A new `content_blocks` property (or `contentBlocks` in JavaScript) provides unified access to modern LLM features across all providers[^2][^3]. This standardization allows developers to work with features like vision, audio, and other content types consistently regardless of the underlying model provider[^3].

**Currently supported in:**
- `langchain`
- `@langchain/core`
- `@langchain/anthropic`
- `@langchain/openai`[^3]

### 3. **Middleware System**

LangChain v1.0 introduces a new middleware concept that provides flexibility in how agents process requests and responses[^1]. The framework includes prebuilt middlewares for common patterns[^2]:

- **PIIMiddleware**: Redacts sensitive information before sending data to the model
- **SummarizationMiddleware**: Condenses conversation history when it becomes too long
- **HumanInTheLoopMiddleware**: Requires approval for sensitive tool calls[^2]

### 4. **Simplified Package Scope**

The v1.0 release significantly reduces the package scope to focus on essential abstractions[^1]. Legacy functionality has been moved to `langchain-classic` for backwards compatibility, allowing the core package to remain streamlined and powerful[^1].

## Production-Ready Foundation

LangChain v1.0 is designed as a "focused, production-ready foundation for building agents"[^2]. The framework streamlines around three core improvements to support developers in shipping AI features quickly with standardized model abstractions and prebuilt agent patterns[^1].

## Integration with LangGraph v1.0

LangChain v1.0 works hand-in-hand with LangGraph v1.0, which serves as the underlying agent runtime[^2]. LangGraph v1.0 maintains stable core APIs while refining type safety, documentation, and developer ergonomics, allowing developers to start with high-level abstractions and drop down to granular control when needed[^2].

## Stability Commitment

Both LangChain and LangGraph v1.0 releases mark a commitment to stability for the open-source libraries with **no breaking changes until v2.0**[^1]. This provides developers with confidence in building production systems on these frameworks.

## Key Features Summary

| Feature | Description |
|---------|-------------|
| **create_agent API** | New standard for building agents, replacing create_react_agent |
| **Standard Content Blocks** | Unified access to modern LLM features across providers |
| **Middleware System** | Flexible request/response processing with prebuilt options |
| **Simplified Namespace** | Focused on core abstractions, legacy features in langchain-classic |
| **Production Ready** | Stability commitment with no breaking changes until v2.0 |
| **LangGraph Integration** | Built on top of battle-tested LangGraph runtime |

---

## References

[^1]: LangChain and LangGraph Agent Frameworks Reach v1.0 Milestones - https://blog.langchain.com/langchain-langgraph-1dot0/

[^2]: What's new in v1 (Python Documentation) - https://docs.langchain.com/oss/python/releases/langchain-v1

[^3]: What's new in v1 (JavaScript Documentation) - https://docs.langchain.com/oss/javascript/releases/langchain-v1
