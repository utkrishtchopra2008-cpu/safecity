import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

const frontendDirectory = path.dirname(fileURLToPath(import.meta.url));
const repositoryRoot = path.resolve(frontendDirectory, '..');

export default defineConfig(({ mode }) => {
  const environment = loadEnv(mode, repositoryRoot, '');
  const apiProxyTarget = environment.API_PROXY_TARGET || 'http://127.0.0.1:8000';

  return {
    envDir: repositoryRoot,
    plugins: [react()],
    server: {
      host: '127.0.0.1',
      port: 5173,
      strictPort: true,
      proxy: {
        '/api': { target: apiProxyTarget, changeOrigin: false },
        '/health': { target: apiProxyTarget, changeOrigin: false },
      },
    },
  };
});
