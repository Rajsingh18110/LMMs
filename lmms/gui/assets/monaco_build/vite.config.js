import { defineConfig } from 'vite';

export default defineConfig({
  base: './', // relative paths for embedding
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
  optimizeDeps: {
    include: ['monaco-editor', 'monaco-languageclient', 'vscode-ws-jsonrpc']
  }
});
