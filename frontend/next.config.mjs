/** @type {import('next').NextConfig} */
const nextConfig = {
  // バックエンドAPIへのプロキシ設定（必要に応じて有効化）
  // async rewrites() {
  //   return [
  //     {
  //       source: '/api/:path*',
  //       destination: 'http://localhost:8000/api/:path*',
  //     },
  //   ];
  // },
};

export default nextConfig;
