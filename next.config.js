/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverActions: {
      bodySizeLimit: '50mb',
    },
  },
  webpack: (config, { dev, isServer }) => {
    if (dev) {
      // Avoid watching dirs that can hang on Windows/OneDrive
      config.watchOptions = config.watchOptions || {};
      config.watchOptions.ignored = [
        '**/node_modules/**',
        '**/.next/**',
        '**/workspaces/**',
        '**/data/**',
        '**/.git/**',
        '**/Backend/**',
        '**/examples/**',
        '**/*.zip',
      ];
      config.watchOptions.aggregateTimeout = 500;
    }
    return config;
  },
};

module.exports = nextConfig;
