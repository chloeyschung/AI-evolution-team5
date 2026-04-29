import { defineConfig } from 'vite';
import { resolve } from 'path';
import { readFileSync, writeFileSync, copyFileSync, existsSync } from 'fs';
import { mkdir } from 'fs/promises';

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

import { copyFileSync as syncCopy, mkdirSync as syncMkdir } from 'fs';

// Plugin to copy static assets and update manifest.json after build
function extensionBuilderPlugin() {
  return {
    name: 'extension-builder',
    closeBundle() {
      console.log('📦 Copying static assets and updating manifest...');

      const srcDir = resolve(__dirname, 'src');
      const distDir = resolve(__dirname, 'dist');

      // Helper to copy file with sync mkdir
      const copyFile = (src: string, dest: string) => {
        const destDir = dest.substring(0, dest.lastIndexOf('/'));
        if (destDir) {
          syncMkdir(destDir, { recursive: true });
        }
        syncCopy(src, dest);
      };

      // Files to copy: HTML and CSS
      const filesToCopy = [
        { src: 'popup/popup.html', dest: 'popup/popup.html', transform: (content: string) =>
          content.replace('src="popup.ts"', 'src="popup.js"')
        },
        { src: 'popup/popup.css', dest: 'popup/popup.css' },
        { src: 'login/login.html', dest: 'login/login.html', transform: (content: string) =>
          content.replace('src="login.ts"', 'src="login.js"')
        },
        { src: 'login/login.css', dest: 'login/login.css' },
        { src: 'content/content-script.css', dest: 'content/content-script.css' },
        { src: 'styles/tokens.css', dest: 'styles/tokens.css' },
      ];

      // Copy files
      for (const { src, dest, transform } of filesToCopy) {
        const srcPath = resolve(srcDir, src);
        const destPath = resolve(distDir, dest);

        if (existsSync(srcPath)) {
          let content = readFileSync(srcPath, 'utf-8');
          if (transform) {
            content = transform(content);
          }
          // Ensure dest directory exists
          const destDir = destPath.substring(0, destPath.lastIndexOf('/'));
          if (destDir) {
            syncMkdir(destDir, { recursive: true });
          }
          writeFileSync(destPath, content);
          console.log(`  ✓ Copied ${src} → ${dest}`);
        }
      }

      // Update manifest.json - change src/ to relative paths and .ts to .js
      // Paths must be relative to manifest.json location (which is in dist/)
      const manifestPath = resolve(__dirname, 'manifest.json');
      const manifestContent = readFileSync(manifestPath, 'utf-8');
      const manifest = JSON.parse(manifestContent);

      // Update service worker path: src/background/service-worker.ts → background/service-worker.js
      if (manifest.background?.service_worker) {
        manifest.background.service_worker = manifest.background.service_worker
          .replace('src/', '')
          .replace('.ts', '.js');
      }

      // Update content scripts - add type: "module" for ES module support
      if (manifest.content_scripts) {
        manifest.content_scripts.forEach((script: any) => {
          if (script.js) {
            script.js = script.js.map((file: string) =>
              file.replace('src/', '').replace('.ts', '.js')
            );
          }
          if (script.css) {
            script.css = script.css.map((file: string) =>
              file.replace('src/', '')
            );
          }
        });
      }

      // Update action popup
      if (manifest.action?.default_popup) {
        manifest.action.default_popup = manifest.action.default_popup
          .replace('src/', '');
      }

      // Update web_accessible_resources
      if (manifest.web_accessible_resources) {
        manifest.web_accessible_resources.forEach((resource: any) => {
          if (resource.resources) {
            resource.resources = resource.resources.map((file: string) =>
              file.replace('src/', '')
            );
          }
        });
      }

      // Copy icons to dist/
      const iconsSrc = resolve(__dirname, 'icons');
      const iconsDest = resolve(distDir, 'icons');
      if (existsSync(iconsSrc)) {
        syncMkdir(iconsDest, { recursive: true });
        const iconFiles = ['icon16.png', 'icon48.png', 'icon128.png'];
        for (const icon of iconFiles) {
          const srcPath = resolve(iconsSrc, icon);
          const destPath = resolve(iconsDest, icon);
          if (existsSync(srcPath)) {
            syncCopy(srcPath, destPath);
            console.log(`  ✓ Copied icons/${icon} → dist/icons/${icon}`);
          }
        }
      }

      // Write updated manifest to dist/ (Chrome expects manifest.json at extension root)
      const distManifestPath = resolve(distDir, 'manifest.json');
      writeFileSync(distManifestPath, JSON.stringify(manifest, null, 2) + '\n');
      console.log('  ✓ Copied manifest.json → dist/manifest.json');
      console.log('✅ Build complete! Load dist/ in Chrome.');
    },
  };
}

export default defineConfig({
  envPrefix: 'VITE_',
  define: {
    __BRIEFLY_CONFIG: JSON.stringify({
      GOOGLE_CLIENT_ID: env.VITE_GOOGLE_CLIENT_ID || '',
      API_BASE_URL: env.VITE_API_BASE_URL || '',
      SHOW_API_URL_SETTING: env.VITE_SHOW_API_URL_SETTING === 'true',
    }),
  },
  plugins: [extensionBuilderPlugin()],
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
