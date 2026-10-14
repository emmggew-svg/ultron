/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // openultron servisi bu klasörü statik export alıp :3030'dan sunar
  output: "export",
  images: { unoptimized: true },
  webpack: (config) => {
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': require('path').resolve(__dirname),
      '@/components': require('path').resolve(__dirname, 'components'),
    };
    return config;
  },
};

module.exports = nextConfig;
