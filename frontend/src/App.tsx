import { BrowserRouter as Router, Navigate, Routes, Route, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import Layout from './components/layout/Layout'
import AdminDashboardPage from './pages/AdminDashboardPage'
import AstroCommunityPage from './pages/AstroCommunityPage'
import PaymentPage from './pages/PaymentPage'
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

function MainPlatformRedirect() {
  const cleanupAndOpen = async () => {
    try {
      if ('serviceWorker' in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations();
        await Promise.all(registrations.map((registration) => registration.unregister()));
      }
      if ('caches' in window) {
        const keys = await caches.keys();
        await Promise.all(keys.filter((key) => key.startsWith('kundali-')).map((key) => caches.delete(key)));
      }
    } catch (error) {
      console.warn('Unable to clear stale platform cache.', error);
    }

    const target = `/index.html?legacy=${Date.now()}`;
    if (window.location.pathname !== '/index.html' || !window.location.search.includes('legacy=')) {
      window.location.replace(target);
    }
  };

  cleanupAndOpen();
  return <PageState title="Opening platform" message="Clearing stale cache and opening the main Shree Lakshmi Astro platform." />;
}

function ProtectedRoute({ children, allowedRoles }: { children: ReactNode; allowedRoles: Role[] }) {
  const { session, loading } = useAuth();
  const location = useLocation();
  if (loading) return <PageState title="Checking access" message="Please wait while we verify your session." />;
  if (!session?.access_token) return <Navigate to="/" replace state={{ from: location.pathname }} />;
  const role = (session.user?.role || (session.user?.user_metadata as any)?.role || 'user') as Role;
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
          <Route index element={<MainPlatformRedirect />} />
          <Route path="payment" element={<PaymentPage />} />
          <Route path="astro-community" element={<ProtectedRoute allowedRoles={['admin', 'astrologer_verified', 'astrologer_pending', 'user']}><AstroCommunityPage /></ProtectedRoute>} />
          <Route path="admin" element={<ProtectedRoute allowedRoles={['admin']}><AdminDashboardPage /></ProtectedRoute>} />
          <Route path="*" element={<MainPlatformRedirect />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App
