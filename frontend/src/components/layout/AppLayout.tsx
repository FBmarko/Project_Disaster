import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import { Navbar } from '@/components/layout/Navbar'
import { Sidebar } from '@/components/layout/Sidebar'

const SIDEBAR_ID = 'app-sidebar'

/** Shell shared by every route: navbar, drawer sidebar and the routed content. */
export function AppLayout() {
  const [isSidebarOpen, setSidebarOpen] = useState(false)

  // Prevent the page behind the drawer from scrolling while it is open.
  useEffect(() => {
    if (!isSidebarOpen) return

    const previous = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.body.style.overflow = previous
    }
  }, [isSidebarOpen])

  return (
    <div className="min-h-dvh overflow-x-hidden bg-surface">
      <Navbar
        onOpenSidebar={() => setSidebarOpen(true)}
        sidebarId={SIDEBAR_ID}
        isSidebarOpen={isSidebarOpen}
      />

      <Sidebar
        id={SIDEBAR_ID}
        isOpen={isSidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="px-3 py-3 sm:px-6 sm:py-6">
        <Outlet />
      </main>
    </div>
  )
}
