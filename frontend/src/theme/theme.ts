export const THEME_STORAGE_KEY = 'afet360-theme'

export type Theme = 'light' | 'dark'

type ThemeStorage = Pick<Storage, 'getItem' | 'setItem'>

export function parseTheme(value: unknown): Theme | null {
  return value === 'light' || value === 'dark' ? value : null
}

export function resolveTheme(storedValue: unknown, prefersDark: boolean): Theme {
  return parseTheme(storedValue) ?? (prefersDark ? 'dark' : 'light')
}

export function readStoredTheme(storage: ThemeStorage | null): Theme | null {
  if (!storage) return null
  try {
    return parseTheme(storage.getItem(THEME_STORAGE_KEY))
  } catch {
    return null
  }
}

export function writeStoredTheme(storage: ThemeStorage | null, theme: Theme): boolean {
  if (!storage) return false
  try {
    storage.setItem(THEME_STORAGE_KEY, theme)
    return true
  } catch {
    return false
  }
}

export function applyTheme(theme: Theme, root: HTMLElement = document.documentElement) {
  root.classList.toggle('dark', theme === 'dark')
  root.style.colorScheme = theme
}
