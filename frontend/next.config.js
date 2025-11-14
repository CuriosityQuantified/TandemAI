/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        // Don't proxy /api/copilotkit as it's handled by Next.js API route
        source: '/api/:path((?!copilotkit).*)',
        destination: 'http://localhost:8000/api/:path*',
      },
    ]
  },
}

module.exports = nextConfig