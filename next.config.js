/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverActions: {
      bodySizeLimit: '50mb',
    },
  },
  webpack: (config, { dev, isServer }) => {
    if (dev) {
      // Avoid watching uploaded workspaces/data (can hang on Windows/OneDrive)
      config.watchOptions = config.watchOptions || {};
        config.watchOptions.ignored = [
          '**/node_modules/**',
          '**/.next/**',
          '**/workspaces/**',
          '**/data/**',
          '**/.git/**',
        ];
        config.watchOptions.aggregateTimeout = 300;
    }
    return config;
  },
};

module.exports = nextConfig;
