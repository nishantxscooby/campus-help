import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  const target = loadEnv(mode, process.cwd(), 'CAMPUS_HELP_').CAMPUS_HELP_API_ORIGIN || 'http://127.0.0.1:8000';
  return { server: { proxy: { '/ask': target, '/documents': target, '/health': target } } };
});
