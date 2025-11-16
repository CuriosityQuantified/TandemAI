import {
  CopilotRuntime,
  OpenAIAdapter,
  copilotRuntimeNextJSAppRouterEndpoint
} from "@copilotkit/runtime";
import { LangGraphHttpAgent } from "@ag-ui/langgraph";
import { NextRequest } from "next/server";

// Backend AG-UI endpoint URL
// In development: http://localhost:8000/copilotkit
// In production: Set via AGENT_URL environment variable
const AGENT_URL = process.env.AGENT_URL || "http://localhost:8000/copilotkit";

// Service adapter - OpenAI for peripheral features (chat suggestions, etc.)
// The LangGraph agent handles main chat logic
const serviceAdapter = new OpenAIAdapter();

// Create CopilotRuntime with LangGraph HTTP agent
// This connects the frontend to the backend AG-UI endpoint
const runtime = new CopilotRuntime({
  agents: {
    research_agent: new LangGraphHttpAgent({
      url: AGENT_URL,
    }),
  },
});

// Next.js App Router API endpoint handler
// This endpoint acts as a proxy between frontend and backend
export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};
