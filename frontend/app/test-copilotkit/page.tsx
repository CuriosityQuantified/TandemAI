"use client";

import { CopilotChat } from "@copilotkit/react-ui";
import { useCoAgent } from "@copilotkit/react-core";

export default function TestCopilotKit() {
  // Test state connection with research agent
  const { state, setState } = useCoAgent({
    name: "research_agent",
    initialState: {
      test_message: "Hello from frontend!",
      plan_steps: [],
      resources: [],
      report: "",
    },
  });

  return (
    <div className="flex h-screen bg-gray-50">
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="p-4 bg-white border-b shadow-sm">
          <h1 className="text-2xl font-bold text-gray-800">
            CopilotKit Connection Test
          </h1>
          <p className="text-sm text-gray-600 mt-1">
            Testing connection to backend AG-UI endpoint at{" "}
            <code className="bg-gray-100 px-2 py-1 rounded text-xs">
              http://localhost:8000/copilotkit
            </code>
          </p>
        </div>

        {/* State Display */}
        <div className="p-4 bg-blue-50 border-b">
          <div className="flex items-center justify-between mb-2">
            <h3 className="font-semibold text-blue-900">Agent State:</h3>
            <button
              onClick={() =>
                setState({
                  ...state,
                  test_message: `Updated at ${new Date().toLocaleTimeString()}`,
                })
              }
              className="text-xs bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700"
            >
              Update State
            </button>
          </div>
          <pre className="text-xs bg-white p-3 rounded border border-blue-200 overflow-auto max-h-32">
            {JSON.stringify(state, null, 2)}
          </pre>
        </div>

        {/* CopilotKit Chat */}
        <div className="flex-1 overflow-hidden">
          <CopilotChat
            instructions="You are a research assistant. This is a connection test. Respond to user messages to verify the backend connection is working."
            labels={{
              title: "TandemAI Connection Test",
              initial:
                "Connection test ready! Send a message to verify backend communication.",
            }}
            className="h-full"
          />
        </div>
      </div>

      {/* Connection Status Panel */}
      <div className="w-80 border-l bg-white p-4 overflow-y-auto">
        <h2 className="text-lg font-bold mb-4 text-gray-800">
          Connection Status
        </h2>

        <div className="space-y-4">
          {/* Frontend Status */}
          <div className="border rounded-lg p-3 bg-green-50 border-green-200">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
              <span className="font-semibold text-green-900">Frontend</span>
            </div>
            <p className="text-xs text-green-700">
              ✓ CopilotKit provider loaded
            </p>
            <p className="text-xs text-green-700">
              ✓ useCoAgent hook active
            </p>
            <p className="text-xs text-green-700">
              ✓ Runtime URL: /api/copilotkit
            </p>
          </div>

          {/* Backend Connection Instructions */}
          <div className="border rounded-lg p-3 bg-yellow-50 border-yellow-200">
            <div className="flex items-center gap-2 mb-2">
              <span className="font-semibold text-yellow-900">Backend</span>
            </div>
            <p className="text-xs text-yellow-700 mb-2">
              Before testing, start the backend:
            </p>
            <pre className="text-xs bg-gray-900 text-green-400 p-2 rounded overflow-auto">
{`cd backend
source ../.venv/bin/activate
python copilotkit_main_simple.py`}
            </pre>
          </div>

          {/* Test Instructions */}
          <div className="border rounded-lg p-3 bg-blue-50 border-blue-200">
            <h3 className="font-semibold text-blue-900 mb-2">Test Steps:</h3>
            <ol className="text-xs text-blue-700 space-y-1 list-decimal list-inside">
              <li>Start backend (see above)</li>
              <li>Send a test message in chat</li>
              <li>Check browser console (F12)</li>
              <li>Verify backend logs show activity</li>
              <li>Click "Update State" button</li>
              <li>Verify state updates in JSON display</li>
            </ol>
          </div>

          {/* Expected Responses */}
          <div className="border rounded-lg p-3 bg-gray-50 border-gray-200">
            <h3 className="font-semibold text-gray-900 mb-2">
              Expected Results:
            </h3>
            <ul className="text-xs text-gray-700 space-y-1">
              <li>✓ No console errors</li>
              <li>✓ Backend receives POST requests</li>
              <li>✓ Chat messages send successfully</li>
              <li>✓ Agent responds to messages</li>
              <li>✓ State updates reflect in JSON</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
