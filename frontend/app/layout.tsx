import type { Metadata } from 'next';
import './globals.css';
import { AuthProvider } from '@/contexts/AuthContext';
import { CopilotKit } from '@copilotkit/react-core';
import '@copilotkit/react-ui/styles.css';

export const metadata: Metadata = {
  title: 'TandemAI Research Assistant',
  description: 'AI-powered research assistant with CopilotKit',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <CopilotKit
          runtimeUrl="/api/copilotkit"
          showDevConsole={true}
        >
          <AuthProvider>
            {children}
          </AuthProvider>
        </CopilotKit>
      </body>
    </html>
  );
}
