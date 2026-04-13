import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
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
