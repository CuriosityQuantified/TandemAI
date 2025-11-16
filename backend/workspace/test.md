# LangChain v1.0 Features Summary

## Overview
LangChain v1.0 is the first major stable release of the LangChain framework, marking a significant milestone in production-ready agent engineering[^1]. It focuses on streamlining the framework around essential abstractions for building agents[^2].

## Three Core Improvements

### 1. createAgent API
A new standard way to build agents, replacing `createReactAgent` from LangGraph with a cleaner, more powerful API[^2]. The implementation is built on top of LangGraph to leverage the underlying agent runtime and has been battle-tested over the past year[^3].

### 2. Standard Content Blocks
A new `contentBlocks` property provides unified access to modern LLM features across all providers[^2]. This addresses how LLM APIs have evolved from string-based content to message-based structures with lists of content blocks[^3].

**Key improvements**:
- Structured output generated in the main loop (no additional LLM call required)
- Models can choose between calling tools or using provider-side structured output
- Cost reduction by eliminating extra LLM calls[^2]

### 3. Middleware Pattern
A new middleware concept that brings context engineering to the forefront[^4]. Enables developers to design intelligent boundaries between computation stages, control data flow, and enforce execution patterns[^4].

**Common use cases**:
- Input guardrails (PII redaction)
- Conversation summarization
- Human-in-the-loop approval patterns
- Tool error handling via `wrapToolCall`[^5]

## Package Restructuring

LangChain v1.0 reduces package scope to essential abstractions[^1]. Legacy functionality moves to `@langchain/classic` for backwards compatibility, keeping the core package lean and focused[^2].

## LangGraph v1.0 Integration

LangGraph v1.0 is a stability-focused release designed to work seamlessly with LangChain v1[^6]. Battle-tested by companies like Uber, LinkedIn, and Klarna in production[^3].

**Key capabilities**:
- Durable state: Execution state persists automatically
- Built-in persistence: Save and resume workflows without custom database logic
- Stable core APIs with no breaking changes
- Supports arbitrary workflows and agentic patterns[^7]

## Multi-Agent Systems Simplification

Multi-agent systems can now be defined directly in LangChain without a separate orchestration layer[^4]. The entire workflow can live within a single, declarative pipeline, enabling supervisor agents to dynamically spawn and manage subordinate agents[^4].

## Documentation Improvements

LangChain launched a completely redesigned documentation site at docs.langchain.com[^1]. For the first time, all LangChain and LangGraph documentation—across Python and JavaScript—live in one unified site with parallel examples, shared guides, and consolidated API references[^1].

## Stability Commitment

The v1.0 releases mark a commitment to stability with no breaking changes until version 2.0[^1].

## Removed APIs

Notable deprecated APIs removed in v1[^5]:
- `TraceGroup` - Use LangSmith tracing instead
- `BaseDocumentLoader.loadAndSplit` - Use `.load()` followed by a text splitter
- `RemoteRunnable` - No longer supported
- `BasePromptTemplate.serialize` and `.deserialize` - Use JSON serialization
- `ChatPromptTemplate.fromPromptMessages` - Use `ChatPromptTemplate.fromMessages`

---

## References

[^1]: LangChain and LangGraph Agent Frameworks Reach v1.0 Milestones - https://blog.langchain.com/langchain-langgraph-1dot0/

[^2]: What's new in v1 (JavaScript) - https://docs.langchain.com/oss/javascript/releases/langchain-v1

[^3]: LangChain & LangGraph 1.0 alpha releases - https://blog.langchain.com/langchain-langchain-1-0-alpha-releases/

[^4]: LangChain 1.0 — A second look - https://medium.com/mitb-for-all/langchain-a-second-look-6ed720e27fec

[^5]: LangChain v1 migration guide - https://docs.langchain.com/oss/javascript/migrate/langchain-v1

[^6]: What's new in v1 (Python) - https://docs.langchain.com/oss/python/releases/langgraph-v1

[^7]: LangGraph 1.0 is now generally available - https://changelog.langchain.com/announcements/langgraph-1-0-is-now-generally-available
