import { BrowserRouter as Router, Navigate, Routes, Route, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import Layout from './components/layout/Layout'
import HomePage from './pages/HomePage'
import PrashnaPage from './pages/PrashnaPage'
import PrashnaResultPage from './pages/PrashnaResultPage'
import AdminDashboardPage from './pages/AdminDashboardPage'
import AstroCommunityPage from './pages/AstroCommunityPage'
import LegalPage from './pages/LegalPage'
import { useAuth } from './auth/useAuth'

type Role = 'user' | 'astrologer_pending' | 'astrologer_verified' | 'admin';

function PageState({ title, message }: { title: string; message: string }) {
  return (
    <main className="app-page app-page--narrow">
      <section className="state-panel" role="status">
        <h1>{title}</h1>
        <p>{message}</p>
      </section>
    </main>
  );
}

function AccessDenied({ message }: { message: string }) {
  return <PageState title="Access denied" message={message} />;
}

function ProtectedRoute({ children, allowedRoles }: { children: ReactNode; allowedRoles: Role[] }) {
  const { session, loading } = useAuth();
  const location = useLocation();
  if (loading) return <PageState title="Checking access" message="Please wait while we verify your session." />;
  if (!session?.access_token) return <Navigate to="/" replace state={{ from: location.pathname }} />;
  const role = session.user?.role || 'user';
  if (!allowedRoles.includes(role)) {
    return <AccessDenied message="You do not have access to this workspace." />;
  }
  return children;
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<HomePage />} />
          <Route path="prashna" element={<PrashnaPage />} />
          <Route path="prashna-result" element={<PrashnaResultPage />} />
          <Route path="return-policy" element={<LegalPage kind="return" />} />
          <Route path="refund-policy" element={<LegalPage kind="refund" />} />
          <Route path="privacy-policy" element={<LegalPage kind="privacy" />} />
          <Route path="disclaimer" element={<LegalPage kind="disclaimer" />} />
          <Route path="about-contact" element={<LegalPage kind="about-contact" />} />
          <Route path="astro-community" element={<ProtectedRoute allowedRoles={['admin', 'astrologer_verified']}><AstroCommunityPage /></ProtectedRoute>} />
          <Route path="admin" element={<ProtectedRoute allowedRoles={['admin']}><AdminDashboardPage /></ProtectedRoute>} />
          {/* Add more routes here as we migrate */}
          <Route path="*" element={<PageState title="Page not found" message="This page is not available in the React app." />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App
