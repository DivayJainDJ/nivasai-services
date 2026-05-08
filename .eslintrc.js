module.exports = {
  root: true,
  env: {
    es6: true,
    node: true,
    jest: true,
  },
  extends: [
    'eslint:recommended',
    '@typescript-eslint/recommended',
    'google',
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    project: ['tsconfig.json', 'tsconfig.dev.json'],
    sourceType: 'module',
  },
  ignorePatterns: [
    '/lib/**/*',
    '/generated/**/*',
    '*.js',
  ],
  plugins: [
    '@typescript-eslint',
    'import',
  ],
  rules: {
    'quotes': ['error', 'single'],
    'import/no-unresolved': 0,
    'indent': ['error', 2],
    'max-len': ['error', { code: 120 }],
    'object-curly-spacing': ['error', 'always'],
    'camelcase': 'off',
    '@typescript-eslint/naming-convention': [
      'error',
      {
        selector: 'interface',
        format: ['PascalCase'],
        prefix: ['I'],
      },
      {
        selector: 'typeAlias',
        format: ['PascalCase'],
        prefix: ['T'],
      },
      {
        selector: 'enum',
        format: ['PascalCase'],
        suffix: ['Enum'],
      },
    ],
    '@typescript-eslint/explicit-function-return-type': 'warn',
    '@typescript-eslint/explicit-module-boundary-types': 'warn',
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/no-unused-vars': 'error',
    '@typescript-eslint/prefer-const': 'error',
    'require-jsdoc': 'off',
    'valid-jsdoc': 'off',
  },
}
