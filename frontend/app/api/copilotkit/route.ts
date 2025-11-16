import { CopilotRuntime, copilotRuntimeNextJSAppRouterEndpoint } from "@copilotkit/runtime";
import { LangGraphHttpAgent } from "@ag-ui/langgraph";
import { NextRequest } from "next/server";

// Backend AG-UI endpoint URL
// In development: http://localhost:8000/copilotkit
// In production: Set via NEXT_PUBLIC_API_URL environment variable
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Create CopilotRuntime with LangGraph agent
// This connects the frontend to the backend AG-UI endpoint
const runtime = new CopilotRuntime({
  agents: {
    research_agent: new LangGraphHttpAgent({
      url: `${BACKEND_URL}/copilotkit`,
    }),
  },
});

// Next.js App Router API endpoint handler
// This endpoint acts as a proxy between frontend and backend
export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};
