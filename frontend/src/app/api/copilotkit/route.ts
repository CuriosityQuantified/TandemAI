import {
  CopilotRuntime,
  OpenAIAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { NextRequest } from "next/server";

/**
 * CopilotKit Runtime Endpoint
 * This handles the GraphQL communication protocol that CopilotKit expects
 * Actions are defined in the frontend components, not here
 */

// Create a simple runtime without embedded actions
const runtime = new CopilotRuntime();

// Configure the OpenAI adapter
const serviceAdapter = new OpenAIAdapter({
  apiKey: process.env.OPENAI_API_KEY,
  model: "gpt-4",
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });

  return handleRequest(req);
};

// Also handle GET requests for health checks
export const GET = async () => {
  return new Response(
    JSON.stringify({
      status: "ok",
      message: "CopilotKit runtime endpoint is running"
    }),
    {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }
  );
};