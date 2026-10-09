// @ts-check
// Règles de la charte (CLAUDE.md) vérifiables par ESLint, sur la configuration de @nuxt/eslint.
import withNuxt from './.nuxt/eslint.config.mjs'

export default withNuxt(
  {
    rules: {
      // [ZERO-ANY] : `unknown` puis un rétrécissement de type.
      '@typescript-eslint/no-explicit-any': 'error',
    },
  },
  {
    // [APPELS-API] : un composant ou une page passe par un composable du domaine.
    files: ['**/*.vue'],
    rules: {
      'no-restricted-globals': ['error', { name: '$fetch', message: 'Passer par un composable (CLAUDE.md [APPELS-API]).' }],
    },
  },
)
