import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from '@/components/layout/AppLayout'
import { ROUTES } from '@/constants/routes'
import { AboutPage } from '@/pages/AboutPage'
import { AssemblyAreasPage } from '@/pages/AssemblyAreasPage'
import { FaultLinesPage } from '@/pages/FaultLinesPage'
import { HomePage } from '@/pages/HomePage'
import { PreparednessGuidePage } from '@/pages/PreparednessGuidePage'
import { SimulationPage } from '@/pages/SimulationPage'

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
