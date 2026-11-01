import { defineConfig } from 'vitest/config';

export default defineConfig({
  resolve: { alias: { '@': import.meta.dirname } },
  test: {
    include: ['tests/**/*.test.ts'],
    fileParallelism: false,
    hookTimeout: 120_000,
    testTimeout: 15_000,
  },
});
