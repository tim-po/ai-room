import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';

// The bundle is served by Flask from club/static/app; Flask's spa.html reads the manifest to find
// the hashed entry file. No dev server: `npm run dev` rebuilds on change (the site CSP allows only
// same-origin scripts and no inline code).
export default defineConfig({
  plugins: [react()],
  base: '/static/app/',
  build: {
    outDir: '../club/static/app',
    emptyOutDir: true,
    manifest: true,
    rollupOptions: {input: 'src/main.tsx'},
  },
});
