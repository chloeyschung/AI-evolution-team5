import { defineConfig } from 'vite';
import { resolve } from 'path';
import { readFileSync } from 'fs';

// Load environment variables
function loadEnv(): Record<string, string> {
  const envPath = resolve(__dirname, '.env');
  try {
    const envContent = readFileSync(envPath, 'utf-8');
    const env: Record<string, string> = {};
    envContent.split('\n').forEach(line => {
      const match = line.match(/^([^=#\s]+)=(.+)$/);
      if (match) {
        env[match[1]] = match[2].trim();
      }
    });
    return env;
  } catch {
    return {};
  }
}

const env = loadEnv();

export default defineConfig({
  envPrefix: 'VITE_',
  define: {
    __BRIEFLY_CONFIG: JSON.stringify({
      GOOGLE_CLIENT_ID: env.VITE_GOOGLE_CLIENT_ID || '',
    }),
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        'background/service-worker': resolve(__dirname, 'src/background/service-worker.ts'),
        'content/content-script': resolve(__dirname, 'src/content/content-script.ts'),
        'popup/popup': resolve(__dirname, 'src/popup/popup.ts'),
        'login/login': resolve(__dirname, 'src/login/login.ts'),
      },
      output: {
        entryFileNames: '[name].js',
        chunkFileNames: 'chunks/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      },
    },
  },
  publicDir: false,
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    port: 3000,
  },
});
