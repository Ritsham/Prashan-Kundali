import { BrowserRouter as Router, Navigate, Routes, Route, useLocation } from 'react-router-dom'
import { useEffect, useState, type ReactNode } from 'react'
import Layout from './components/layout/Layout'
import AdminDashboardPage from './pages/AdminDashboardPage'
import AstroCommunityPage from './pages/AstroCommunityPage'
import PaymentPage from './pages/PaymentPage'
import { useAuth } from './auth/useAuth'
import { publicEnv } from './config/env'

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

function communityApplicationTarget(statusData: any): string {
  const status = String(statusData?.status || 'NOT_APPLIED').toUpperCase();
  const canReapplyNow = (() => {
    if (!statusData?.reapply_allowed) return false;
    if (!statusData?.reapply_after) return true;
    const reapplyAfter = new Date(statusData.reapply_after);
    return Number.isNaN(reapplyAfter.getTime()) || reapplyAfter <= new Date();
  })();

  if (status === 'NOT_APPLIED' || (status === 'REJECTED' && canReapplyNow)) {
    return '/community/apply';
  }
  return '/community/application-status';
}

function CommunityRoute({ children }: { children: ReactNode }) {
  const { session, loading } = useAuth();
  const [redirectTo, setRedirectTo] = useState('');
  const [accessError, setAccessError] = useState('');
  const [applicationApproved, setApplicationApproved] = useState(false);
  const role = (session?.user?.role || (session?.user?.user_metadata as any)?.role || 'user') as Role;
  const hasVerifiedAccess = role === 'admin' || role === 'astrologer_verified' || applicationApproved;

  useEffect(() => {
    let cancelled = false;

    async function checkCommunityAccess() {
      setRedirectTo('');
      setAccessError('');
      setApplicationApproved(false);
      if (loading || !session?.access_token || role === 'admin' || role === 'astrologer_verified') return;

      try {
        const response = await fetch(`${publicEnv.apiBaseUrl}/api/community/application/status`, {
          headers: { Authorization: `Bearer ${session.access_token}` },
        });
        if (response.status === 401) {
          if (!cancelled) setRedirectTo('/community/apply');
          return;
        }
        if (!response.ok) throw new Error('Unable to check your community application status.');

        const statusData = await response.json();
        if (!cancelled) {
          if (String(statusData?.status || '').toUpperCase() === 'APPROVED') {
            setApplicationApproved(true);
          } else {
            setRedirectTo(communityApplicationTarget(statusData));
          }
        }
      } catch (error) {
        if (!cancelled) {
          setAccessError(error instanceof Error ? error.message : 'Unable to check community access.');
        }
      }
    }

    checkCommunityAccess();
    return () => {
      cancelled = true;
    };
  }, [loading, role, session?.access_token]);

  useEffect(() => {
    if (redirectTo) window.location.replace(redirectTo);
  }, [redirectTo]);

  useEffect(() => {
    if (!loading && !session?.access_token) setRedirectTo('/community/apply');
  }, [loading, session?.access_token]);

  if (loading) return <PageState title="Checking access" message="Please wait while we verify your session." />;
  if (!session?.access_token) {
    return <PageState title="Sign in required" message="Please sign in before opening Astro Community." />;
  }
  if (hasVerifiedAccess) return children;
  if (accessError) return <AccessDenied message={accessError} />;
  return <PageState title="Checking application" message="Please wait while we check your Astro Community access." />;
}

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Layout />}>
          <Route index element={<MainPlatformRedirect />} />
          <Route path="payment" element={<PaymentPage />} />
          <Route path="astro-community" element={<CommunityRoute><AstroCommunityPage /></CommunityRoute>} />
          <Route path="admin" element={<ProtectedRoute allowedRoles={['admin']}><AdminDashboardPage /></ProtectedRoute>} />
          <Route path="*" element={<MainPlatformRedirect />} />
        </Route>
      </Routes>
    </Router>
  )
}

export default App
