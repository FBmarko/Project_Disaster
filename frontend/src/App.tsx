import { lazy } from 'react'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from '@/components/layout/AppLayout'
import { ROUTES } from '@/constants/routes'

const AboutPage = lazy(() => import('@/pages/AboutPage').then(({ AboutPage }) => ({ default: AboutPage })))
const AssemblyAreasPage = lazy(() => import('@/pages/AssemblyAreasPage').then(({ AssemblyAreasPage }) => ({ default: AssemblyAreasPage })))
const FaultLinesPage = lazy(() => import('@/pages/FaultLinesPage').then(({ FaultLinesPage }) => ({ default: FaultLinesPage })))
const HomePage = lazy(() => import('@/pages/HomePage').then(({ HomePage }) => ({ default: HomePage })))
const PreparednessGuidePage = lazy(() => import('@/pages/PreparednessGuidePage').then(({ PreparednessGuidePage }) => ({ default: PreparednessGuidePage })))
const SimulationPage = lazy(() => import('@/pages/SimulationPage').then(({ SimulationPage }) => ({ default: SimulationPage })))

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path={ROUTES.home} element={<HomePage />} />
          <Route path={ROUTES.faultLines} element={<FaultLinesPage />} />
          <Route path={ROUTES.simulation} element={<SimulationPage />} />
          <Route path={ROUTES.preparednessGuide} element={<PreparednessGuidePage />} />
          <Route path={ROUTES.assemblyAreas} element={<AssemblyAreasPage />} />
          <Route path={ROUTES.about} element={<AboutPage />} />
          <Route path="*" element={<Navigate to={ROUTES.home} replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
