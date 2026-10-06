import pluginVue from 'eslint-plugin-vue'
import { defineConfigWithVueTs, vueTsConfigs } from '@vue/eslint-config-typescript'
import pluginVitest from '@vitest/eslint-plugin'

// ESLint 10 flat config，TS 写法（jiti 运行时支持）
export default defineConfigWithVueTs(
  {
    name: 'app/files-to-lint',
    files: ['**/*.{ts,mts,tsx,vue}'],
  },

  {
    name: 'app/files-to-ignore',
    ignores: ['**/dist/**', '**/dist-ssr/**', '**/coverage/**', '**/node_modules/**'],
  },

  vueTsConfigs.strict,
  vueTsConfigs.stylistic,

  ...pluginVue.configs['flat/recommended'],

  {
    ...pluginVitest.configs.recommended,
    name: 'app/vitest',
    files: ['src/**/*.{test,spec}.{ts,mts}', 'src/**/__tests__/*.{ts,mts}'],
  },
)
