import { defineConfig } from 'vite';
export default defineConfig(({mode})=>({
  base: '/converter/',
  build: { target: 'es2022', outDir: mode==='qa'?'qa-dist':'dist', emptyOutDir: true, rollupOptions: mode==='qa'?{input:['index.html','tests/browser.html']}:{} },
  worker: { format: 'es' },
}));
