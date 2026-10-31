import { defineConfig, build } from 'vite';
import react from '@vitejs/plugin-react';
import { resolve } from 'path';

export default defineConfig({
  plugins: [
    react(),
    {
      name: 'bundle-content-script',
      apply: 'build',
      enforce: 'post',
      async closeBundle() {
        await build({
          configFile: false,
          build: {
            emptyOutDir: false,
            outDir: 'dist',
            rollupOptions: {
              input: resolve(__dirname, 'src/content/content_script.ts'),
              output: {
                format: 'iife',
                entryFileNames: 'src/content/content_script.js',
                inlineDynamicImports: true,
              },
            },
          },
        });
      },
    },
  ],
  publicDir: 'public',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        popup: resolve(__dirname, 'popup.html'),
        dashboard: resolve(__dirname, 'dashboard.html'),
        background: resolve(__dirname, 'src/background/service_worker.ts'),
      },
      output: {
        entryFileNames: (chunkInfo) => {
          if (chunkInfo.name === 'background') {
            return 'src/background/service_worker.js';
          }
          return 'assets/[name]-[hash].js';
        },
        chunkFileNames: 'assets/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
      },
    },
  },
});
