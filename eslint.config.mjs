import js from '@eslint/js'
import prettier from 'eslint-config-prettier'
import pluginVue from 'eslint-plugin-vue'
import globals from 'globals'
import tseslint from 'typescript-eslint'

export default tseslint.config(
  {
    ignores: [
      'dist/**',
      '.contract-tmp/**',
      'artifacts/**',
      'output/**',
      'tmp/**',
      'data/**',
      'node_modules/**',
      'coverage/**',
      'backend/.venv*/**',
      'backend/data/**',
      'backend/**/__pycache__/**',
      'backend/.pytest_cache/**',
      'cloudfunctions/**/node_modules/**',
      'package-lock.json',
      'project.private.config.json',
    ],
  },
  {
    linterOptions: {
      reportUnusedDisableDirectives: 'error',
    },
  },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  ...pluginVue.configs['flat/recommended'],
  {
    files: ['src/**/*.{ts,vue}'],
    languageOptions: {
      globals: {
        console: 'readonly',
        setTimeout: 'readonly',
        clearTimeout: 'readonly',
        uni: 'readonly',
      },
    },
    rules: {
      '@typescript-eslint/no-explicit-any': 'error',
      '@typescript-eslint/no-unused-vars': [
        'error',
        {
          argsIgnorePattern: '^_',
          varsIgnorePattern: '^_',
        },
      ],
      'no-console': ['error', { allow: ['warn', 'error'] }],
      'no-restricted-globals': [
        'error',
        { name: 'window', message: '跨端源码请使用 uni API 或平台适配器。' },
        { name: 'document', message: '跨端源码不能直接访问 DOM。' },
        { name: 'localStorage', message: '请通过 repository 使用 uni storage。' },
        { name: 'sessionStorage', message: '请通过 repository 使用 uni storage。' },
        { name: 'process', message: '客户端源码不能依赖 Node.js 全局。' },
        { name: 'Buffer', message: '客户端源码不能依赖 Node.js Buffer。' },
      ],
      'vue/multi-word-component-names': 'off',
      'vue/no-v-html': 'error',
      'vue/require-default-prop': 'off',
    },
  },
  {
    files: ['src/**/*.vue'],
    languageOptions: {
      parserOptions: {
        parser: tseslint.parser,
        extraFileExtensions: ['.vue'],
      },
    },
  },
  {
    files: ['vite.config.ts', 'vitest.config.ts', 'scripts/wechat/*.mjs'],
    languageOptions: {
      globals: globals.node,
    },
  },
  {
    files: ['cloudfunctions/**/*.js'],
    languageOptions: {
      ecmaVersion: 2022,
      globals: globals.node,
      sourceType: 'commonjs',
    },
    rules: {
      '@typescript-eslint/no-require-imports': 'off',
      'no-console': 'off',
    },
  },
  prettier,
)
