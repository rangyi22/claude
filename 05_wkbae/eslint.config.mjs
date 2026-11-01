import js from '@eslint/js';
import tseslint from 'typescript-eslint';
import prettier from 'eslint-config-prettier';

export default tseslint.config(
  {
    ignores: ['node_modules', 'dist', '.next', 'coverage', '.omc', 'next-env.d.ts', 'test-results'],
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
      'no-console': 'error',
      'func-style': ['error', 'declaration'],
      'prefer-arrow-callback': 'off',
    },
  },
  prettier,
);
