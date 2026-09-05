import { House, Menu, Moon, Sun } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { BrandLogo } from '@/components/common/BrandLogo'
import { ROUTES } from '@/constants/routes'
import { useTheme } from '@/hooks/useTheme'

type NavbarProps = {
  onOpenSidebar: () => void
  /** Id of the sidebar element the menu button controls. */
  sidebarId: string
  isSidebarOpen: boolean
}

const iconButtonClass =
  'inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-xl text-text-primary ' +
  'transition-colors hover:bg-surface active:bg-border-subtle/60'

/**
 * Top bar: menu button (left), centered brand logo, home button (right).
 *
 * The logo sits in the middle track of a `1fr auto 1fr` grid, so it stays at the
 * true horizontal center regardless of the width of the side controls or of the
 * viewport.
 */
export function Navbar({ onOpenSidebar, sidebarId, isSidebarOpen }: NavbarProps) {
  const navigate = useNavigate()
  const { theme, toggleTheme } = useTheme()
  const themeLabel = theme === 'dark' ? 'Açık moda geç' : 'Koyu moda geç'

  return (
    <header className="px-3 pt-3 sm:px-6 sm:pt-6">
      <nav
        aria-label="Ana gezinme"
        className="grid grid-cols-[minmax(0,1fr)_auto_minmax(0,1fr)] items-center gap-0 rounded-2xl border border-border-subtle/70 bg-card px-3 py-2.5 shadow-sm min-[360px]:gap-2 sm:px-5 sm:py-3"
      >
        <div className="flex justify-start">
          <button
            type="button"
            onClick={onOpenSidebar}
            className={iconButtonClass}
            aria-label="Menüyü aç"
            aria-controls={sidebarId}
            aria-expanded={isSidebarOpen}
          >
            <Menu size={26} aria-hidden="true" />
          </button>
        </div>

        <BrandLogo height={18} className="min-[360px]:hidden" />
        <BrandLogo height={30} className="hidden min-[360px]:block sm:hidden" />
        <BrandLogo height={38} className="hidden sm:block" />

        <div className="flex justify-end gap-0.5 min-[360px]:gap-1">
          <button
            type="button"
            onClick={toggleTheme}
            className={iconButtonClass}
            aria-label={themeLabel}
            title={themeLabel}
            aria-pressed={theme === 'dark'}
          >
            {theme === 'dark' ? (
              <Sun size={24} aria-hidden="true" />
            ) : (
              <Moon size={24} aria-hidden="true" />
            )}
          </button>
          <button
            type="button"
            onClick={() => navigate(ROUTES.home)}
            className={iconButtonClass}
            aria-label="Ana sayfaya git"
          >
            <House size={24} aria-hidden="true" />
          </button>
        </div>
      </nav>
    </header>
  )
}
