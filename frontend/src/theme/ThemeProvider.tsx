import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { PropsWithChildren } from 'react'
import { ThemeContext } from './ThemeContext'
import { applyTheme, readStoredTheme, resolveTheme, writeStoredTheme } from './theme'
import type { Theme } from './theme'

const SYSTEM_THEME_QUERY = '(prefers-color-scheme: dark)'

function getStorage(): Storage | null {
  try {
    return window.localStorage
  } catch {
    return null
  }
}

function getInitialTheme(): Theme {
  if (document.documentElement.classList.contains('dark')) return 'dark'

  return resolveTheme(
    readStoredTheme(getStorage()),
    window.matchMedia?.(SYSTEM_THEME_QUERY).matches ?? false,
  )
}

export function ThemeProvider({ children }: PropsWithChildren) {
  const [storage] = useState<Storage | null>(getStorage)
  const [hasInitialPreference] = useState(() => readStoredTheme(storage) !== null)
  const hasExplicitPreference = useRef(hasInitialPreference)
  const [theme, setTheme] = useState<Theme>(getInitialTheme)

  useEffect(() => {
    applyTheme(theme)
  }, [theme])

  useEffect(() => {
    if (hasExplicitPreference.current || !window.matchMedia) return

    const mediaQuery = window.matchMedia(SYSTEM_THEME_QUERY)
    const syncWithSystem = (prefersDark: boolean) => {
      const nextTheme = prefersDark ? 'dark' : 'light'
      applyTheme(nextTheme)
      setTheme(nextTheme)
    }
    const handleChange = (event: MediaQueryListEvent) => {
      if (!hasExplicitPreference.current) syncWithSystem(event.matches)
    }

    syncWithSystem(mediaQuery.matches)
    mediaQuery.addEventListener('change', handleChange)
    return () => mediaQuery.removeEventListener('change', handleChange)
  }, [])

  const toggleTheme = useCallback(() => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark'
    hasExplicitPreference.current = true
    writeStoredTheme(storage, nextTheme)
    applyTheme(nextTheme)
    setTheme(nextTheme)
  }, [storage, theme])

  const value = useMemo(() => ({ theme, toggleTheme }), [theme, toggleTheme])

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}
