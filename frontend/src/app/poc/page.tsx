'use client';

import { useState, useEffect } from 'react';
import { useCopilotAction, useCopilotChat } from '@copilotkit/react-core';

export default function POCPage() {
  const [taskResult, setTaskResult] = useState<any>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [eventSource, setEventSource] = useState<EventSource | null>(null);

  // Use the copilot chat hook to append messages
  const { appendMessage } = useCopilotChat();

  // Clean up SSE connection on unmount
  useEffect(() => {
    return () => {
      if (eventSource) {
        eventSource.close();
      }
    };
  }, [eventSource]);

  // Register a CopilotKit action for task execution
  useCopilotAction({
    name: "executeTask",
    description: "Execute a complex task using the ATLAS agent hierarchy",
    parameters: [
      {
        name: "query",
        type: "string",
        description: "The task or question to analyze",
        required: true,
      },
    ],
    handler: async ({ query }) => {
      console.log("Executing task:", query);
      setIsProcessing(true);
      setTaskResult(null);

      try {
        // Call our backend API directly
        const response = await fetch('/api/tasks', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            description: query,
            type: 'general',
          }),
        });

        if (!response.ok) {
          const errorText = await response.text();
          console.error('Backend error response:', errorText);
          throw new Error(`Backend error: ${response.statusText}`);
        }

        const data = await response.json();
        setTaskResult(data);

        // Set up SSE connection for real-time agent updates
        if (data.task_id) {
          const sse = new EventSource(`/api/agui/stream/${data.task_id}`);

          sse.onmessage = (event) => {
            try {
              const eventData = JSON.parse(event.data);
              console.log('AG-UI Event received:', eventData);

              // Handle different event types - check both 'type' and 'event_type'
              const eventType = eventData.type || eventData.event_type;

              // Extract content from various possible locations
              const content = eventData.content?.data ||
                            eventData.data?.content ||
                            eventData.data?.message ||
                            eventData.message ||
                            eventData.text;

              // Extract agent ID
              const agentId = eventData.agent_id || eventData.data?.agent_id || 'Supervisor';

              console.log('Event type:', eventType, 'Content:', content);

              // Handle different event types and stream to CopilotKit
              if (eventType === 'dialogue_update' || eventType === 'AGENT_DIALOGUE_UPDATE') {
                if (content) {
                  // Check for reasoning vs assistant messages
                  const messageType = eventData.content?.type || eventData.data?.type || 'text';

                  if (messageType === 'reasoning') {
                    // Show internal reasoning with special formatting
                    appendMessage({
                      role: 'assistant',
                      content: `💭 [Thinking]: ${content}`,
                    });
                  } else {
                    // Show agent response
                    appendMessage({
                      role: 'assistant',
                      content: `[${agentId}]: ${content}`,
                    });
                  }
                }
              } else if (eventType === 'tool_call_initiated' || eventType === 'TOOL_CALL_INITIATED') {
                const toolName = eventData.tool_name || eventData.data?.tool_name;
                if (toolName) {
                  appendMessage({
                    role: 'assistant',
                    content: `🔧 Using tool: ${toolName}`,
                  });
                }
              } else if (eventType === 'agent_message_sent' || eventType === 'AGENT_MESSAGE_SENT') {
                const targetAgent = eventData.target_agent || eventData.data?.target_agent;
                appendMessage({
                  role: 'assistant',
                  content: `📤 Delegating to ${targetAgent}: ${content || 'Processing task...'}`,
                });
              } else if (eventType === 'task_progress' || eventType === 'TASK_PROGRESS') {
                const progress = eventData.data?.progress_percentage || 0;
                appendMessage({
                  role: 'system',
                  content: `📊 Progress: ${progress}% - ${content || 'Processing...'}`,
                });
              } else if (eventType === 'task_completed' || eventType === 'TASK_COMPLETED') {
                appendMessage({
                  role: 'assistant',
                  content: `✅ Task completed: ${eventData.data?.result_summary || content || 'Successfully processed'}`,
                });
              } else if (eventType === 'error' || eventType === 'AGENT_ERROR') {
                const errorMessage = eventData.error_message || eventData.data?.error_message || content;
                appendMessage({
                  role: 'system',
                  content: `❌ Error: ${errorMessage}`,
                });
              } else if (eventType === 'connection_established' || eventType === 'ping') {
                // Ignore connection and ping events
                console.log('SSE connection event:', eventType);
              } else {
                // Log unknown event types for debugging
                console.log('Unhandled AG-UI event type:', eventType, eventData);
              }
            } catch (err) {
              console.error('Error parsing SSE event:', err, event.data);
            }
          };

          sse.onerror = (error) => {
            console.error('SSE error:', error);
            sse.close();
          };

          setEventSource(sse);
        }

        return {
          success: true,
          taskId: data.task_id,
          message: `Task created: ${data.message}`,
        };
      } catch (error) {
        console.error('Error executing task:', error);
        const errorResult = {
          success: false,
          error: error instanceof Error ? error.message : "Failed to execute task"
        };
        setTaskResult(errorResult);
        return errorResult;
      } finally {
        setIsProcessing(false);
      }
    },
  });

  // Add agent status action
  useCopilotAction({
    name: "getAgentStatus",
    description: "Get the current status of all agents",
    parameters: [],
    handler: async () => {
      try {
        const response = await fetch('/api/agents');
        if (!response.ok) {
          throw new Error(`Backend error: ${response.statusText}`);
        }
        const agents = await response.json();
        return {
          success: true,
          agents,
        };
      } catch (error) {
        console.error("Error getting agent status:", error);
        return {
          success: false,
          error: error instanceof Error ? error.message : "Unknown error",
        };
      }
    },
  });

  return (
    <div className="h-screen bg-gray-900 text-white overflow-y-auto">
      <div className="max-w-6xl mx-auto p-8">
        <h1 className="text-4xl font-bold mb-8 text-blue-400">
          ATLAS POC - Multi-Agent Task Execution
        </h1>

        <div className="bg-gray-800 rounded-lg p-6 mb-8">
          <h2 className="text-2xl font-semibold mb-4">Agent Hierarchy:</h2>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="bg-gray-700 p-4 rounded">
              <h3 className="font-bold text-blue-400">Supervisor</h3>
              <p className="text-sm">Coordinates all agents</p>
            </div>
            <div className="bg-gray-700 p-4 rounded">
              <h3 className="font-bold text-green-400">Research</h3>
              <p className="text-sm">Gathers information</p>
            </div>
            <div className="bg-gray-700 p-4 rounded">
              <h3 className="font-bold text-yellow-400">Analysis</h3>
              <p className="text-sm">Interprets data</p>
            </div>
            <div className="bg-gray-700 p-4 rounded">
              <h3 className="font-bold text-purple-400">Writing</h3>
              <p className="text-sm">Generates content</p>
            </div>
          </div>
        </div>

        {isProcessing && (
          <div className="bg-blue-900 rounded-lg p-6 mb-8">
            <h2 className="text-2xl font-semibold mb-4">Processing...</h2>
            <div className="animate-pulse">
              <div className="h-2 bg-blue-400 rounded"></div>
            </div>
          </div>
        )}

        {taskResult && (
          <div className="bg-gray-800 rounded-lg p-6">
            <h2 className="text-2xl font-semibold mb-4">Results:</h2>
            <pre className="bg-gray-900 p-4 rounded overflow-x-auto">
              {JSON.stringify(taskResult, null, 2)}
            </pre>
          </div>
        )}
      </div>
    </div>
  );
}