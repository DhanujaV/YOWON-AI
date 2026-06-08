import { Suspense, lazy } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { Shield } from 'lucide-react'

const LandingPage = lazy(() => import('./pages/LandingPage'))
const SubmitPage = lazy(() => import('./pages/SubmitPage'))
const EvaluatePage = lazy(() => import('./pages/EvaluatePage'))
const ReportPage = lazy(() => import('./pages/ReportPage'))
const DemoPage = lazy(() => import('./pages/DemoPage'))
const LeaderboardPage = lazy(() => import('./pages/LeaderboardPage'))
const JuryDashboardPage = lazy(() => import('./pages/JuryDashboardPage'))

function PageLoader() {
  return (
    <div className="min-h-screen grid-bg flex flex-col items-center justify-center gap-4">
      <div className="relative w-14 h-14">
        <div className="absolute inset-0 rounded-full border-4 border-yowon-border" />
        <div className="absolute inset-0 rounded-full border-4 border-t-yowon-accent border-r-transparent border-b-transparent border-l-transparent animate-spin" />
        <Shield size={22} className="absolute inset-0 m-auto text-yowon-accent" />
      </div>
      <p className="text-yowon-muted text-sm font-display tracking-wide">
        Initializing YOWON AI...
      </p>
    </div>
  )
}

function NotFoundPage() {
  return (
    <div className="min-h-screen grid-bg flex flex-col items-center justify-center gap-6 px-4 text-center">
      <h1
        className="text-[8rem] leading-none font-bold font-display text-yowon-border select-none"
        style={{ textShadow: '0 0 60px rgba(6,182,212,0.25)' }}
      >
        404
      </h1>
      <p className="text-yowon-muted max-w-sm">This page doesn't exist in the YOWON AI network.</p>
      <a href="/" className="yowon-btn-primary">Back to Command Center</a>
    </div>
  )
}

function RequireProjectId({ children }: { children: React.ReactNode }) {
  const { pathname } = useLocation()
  const hasId = pathname.split('/').filter(Boolean).length >= 2
  return hasId ? <>{children}</> : <Navigate to="/submit" replace />
}

export default function App() {
  return (
    <Suspense fallback={<PageLoader />}>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/submit" element={<SubmitPage />} />
        <Route path="/demo" element={<DemoPage />} />
        <Route path="/leaderboard" element={<LeaderboardPage />} />
        <Route path="/jury" element={<JuryDashboardPage />} />
        <Route
          path="/evaluate/:projectId"
          element={
            <RequireProjectId>
              <EvaluatePage />
            </RequireProjectId>
          }
        />
        <Route
          path="/report/:projectId"
          element={
            <RequireProjectId>
              <ReportPage />
            </RequireProjectId>
          }
        />
        <Route path="/evaluate" element={<Navigate to="/submit" replace />} />
        <Route path="/report" element={<Navigate to="/submit" replace />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Suspense>
  )
}
