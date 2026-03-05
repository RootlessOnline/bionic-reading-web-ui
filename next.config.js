/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    serverComponentsExternalPackages: ['pdfplumber', 'reportlab', 'pypdf'],
  },
}

module.exports = nextConfig
