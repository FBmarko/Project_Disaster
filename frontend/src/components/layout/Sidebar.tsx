import {
  Activity,
  ClipboardCheck,
  House,
  Info,
  MapPinned,
  Waypoints,
  X,
  type LucideIcon,
} from 'lucide-react'
import { useEffect, useRef } from 'react'
import { NavLink } from 'react-router-dom'
import { BrandLogo } from '@/components/common/BrandLogo'
import { ROUTES } from '@/constants/routes'

type SidebarProps = {
  id: string
  isOpen: boolean
  onClose: () => void
}

type NavItem = {
  label: string
  to: string
  icon: LucideIcon
}

const primaryNavItems: NavItem[] = [
  { label: 'Ana Sayfa', to: ROUTES.home, icon: House },
  { label: 'Fay Hatları', to: ROUTES.faultLines, icon: Waypoints },
  { label: 'Deprem Simülasyonu', to: ROUTES.simulation, icon: Activity },
  {
    label: 'Hazırlık Rehberi',
    to: ROUTES.preparednessGuide,
    icon: ClipboardCheck,
  },
  { label: 'Toplanma Alanları', to: ROUTES.assemblyAreas, icon: MapPinned },
]

const secondaryNavItems: NavItem[] = [
  { label: 'Hakkında', to: ROUTES.about, icon: Info },
]

const itemBaseClass =
  'flex items-center gap-4 rounded-xl px-4 py-3 text-[15px] font-medium transition-colors'
const itemIdleClass = 'text-text-primary hover:bg-surface'
const itemActiveClass = 'bg-brand-red-soft text-brand-red'

function SidebarNavItem({
  item,
  onNavigate,
}: {
  item: NavItem
  onNavigate: () => void
}) {
  const Icon = item.icon

  return (
    <NavLink
      to={item.to}
      end={item.to === ROUTES.home}
      onClick={onNavigate}
      className={({ isActive }) =>
        `${itemBaseClass} ${isActive ? itemActiveClass : itemIdleClass}`
      }
    >
      <Icon size={22} aria-hidden="true" className="shrink-0" />
      <span>{item.label}</span>
    </NavLink>
  )
}

/**
 * Left drawer navigation.
 *
 * Closes via the X button, the overlay, or ESC. Stays mounted so the slide
 * transition works in both directions; it is hidden from assistive tech and
 * removed from the tab order while closed.
 */
export function Sidebar({ id, isOpen, onClose }: SidebarProps) {
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!isOpen) return

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }

    document.addEventListener('keydown', onKeyDown)
    closeButtonRef.current?.focus()

    return () => document.removeEventListener('keydown', onKeyDown)
  }, [isOpen, onClose])

  return (
    <>
      <div
        onClick={onClose}
        aria-hidden="true"
        className={`fixed inset-0 z-40 bg-black/30 transition-opacity duration-200 ${
          isOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
      />

      <aside
        id={id}
        aria-label="Site menüsü"
        aria-hidden={!isOpen}
        inert={!isOpen ? true : undefined}
        className={`fixed top-3 bottom-3 left-3 z-50 flex w-[calc(100vw-1.5rem)] max-w-[340px] flex-col rounded-2xl bg-card shadow-xl transition-transform duration-200 ease-out sm:w-[320px] ${
          isOpen ? 'translate-x-0' : '-translate-x-[calc(100%+0.75rem)]'
        }`}
      >
        <div className="flex items-center justify-between gap-3 px-5 pt-6 pb-2">
          <BrandLogo height={30} />
          <button
            type="button"
            ref={closeButtonRef}
            onClick={onClose}
            aria-label="Menüyü kapat"
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl text-text-primary transition-colors hover:bg-surface"
          >
            <X size={26} aria-hidden="true" />
          </button>
        </div>

        <nav
          aria-label="Sayfalar"
          className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto px-3 pt-4 pb-4"
        >
          {primaryNavItems.map((item) => (
            <SidebarNavItem key={item.to} item={item} onNavigate={onClose} />
          ))}

          <hr className="my-3 border-t border-border-subtle" />

          {secondaryNavItems.map((item) => (
            <SidebarNavItem key={item.to} item={item} onNavigate={onClose} />
          ))}
        </nav>
      </aside>
    </>
  )
}
