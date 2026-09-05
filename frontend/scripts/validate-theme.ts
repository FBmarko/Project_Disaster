import assert from 'node:assert/strict'
import {
  parseTheme,
  readStoredTheme,
  resolveTheme,
  THEME_STORAGE_KEY,
  writeStoredTheme,
} from '../src/theme/theme.ts'

assert.equal(parseTheme('light'), 'light')
assert.equal(parseTheme('dark'), 'dark')
assert.equal(parseTheme('sepia'), null)
assert.equal(parseTheme(null), null)

assert.equal(resolveTheme('dark', false), 'dark')
assert.equal(resolveTheme('light', true), 'light')
assert.equal(resolveTheme(null, true), 'dark')
assert.equal(resolveTheme('invalid', false), 'light')

const values = new Map<string, string>()
const storage = {
  getItem: (key: string) => values.get(key) ?? null,
  setItem: (key: string, value: string) => values.set(key, value),
}

assert.equal(readStoredTheme(storage), null)
assert.equal(writeStoredTheme(storage, 'dark'), true)
assert.equal(values.get(THEME_STORAGE_KEY), 'dark')
assert.equal(readStoredTheme(storage), 'dark')

const unavailableStorage = {
  getItem: () => { throw new Error('Storage unavailable') },
  setItem: () => { throw new Error('Storage unavailable') },
}
assert.equal(readStoredTheme(unavailableStorage), null)
assert.equal(writeStoredTheme(unavailableStorage, 'light'), false)

console.log('PASS: theme values, preference resolution and unavailable storage handling')
