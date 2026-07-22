import React, { useEffect } from 'react';
import { LogOut, Menu, MessageCircle, User, X } from 'lucide-react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../../auth/useAuth';

type NavItem = {
  label: string;
  to: string;
  external?: boolean;
  targetBlank?: boolean;
};

function getProfileInitial(session: ReturnType<typeof useAuth>['session']) {
  const user = session?.user;
  const metadata = user?.user_metadata || {};
  const name = metadata.full_name || metadata.name || user?.email || user?.id || 'User';
  return String(name).trim().charAt(0).toUpperCase() || 'U';
}

const Layout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { session, loading, signIn, signUp, signOut } = useAuth();
  const isCommunityWorkspace = location.pathname === '/astro-community';
  const isHome = location.pathname === '/';
  const [isProfileOpen, setIsProfileOpen] = React.useState(false);
  const [authOpen, setAuthOpen] = React.useState(false);
  const [authMode, setAuthMode] = React.useState<'sign-in' | 'sign-up'>('sign-in');
  const [authError, setAuthError] = React.useState('');
  const [authBusy, setAuthBusy] = React.useState(false);
  const [authForm, setAuthForm] = React.useState({ email: '', password: '', fullName: '' });
  const [mobileNavOpen, setMobileNavOpen] = React.useState(false);
  const isSignedIn = Boolean(session?.access_token);
  const role = session?.user?.role || 'user';
  const canOpenCommunity = role === 'admin' || role === 'astrologer_verified';
  const appNavItems: NavItem[] = [
    { label: 'Home', to: '/index.html', external: true },
    { label: 'Consultant', to: '/consultation', external: true },
    { label: 'Payment', to: '/payment' },
    { label: 'Pricing', to: '/index.html#pricing', external: true },
    { label: 'About', to: '/about.html', external: true },
    ...(canOpenCommunity ? [{ label: 'Astro Community', to: '/astro-community' }] : []),
    ...(role === 'admin' ? [{ label: 'Admin', to: '/admin' }] : []),
  ];
  const navItems = appNavItems;
  const policyItems = [
    { label: 'Return Policy', to: '/return-policy' },
    { label: 'Refund Policy', to: '/refund-policy' },
    { label: 'Privacy Policy', to: '/privacy-policy' },
    { label: 'Disclaimer', to: '/disclaimer' },
    { label: 'About & Contact', to: '/about-contact' },
  ];
  const profileInitial = getProfileInitial(session);
  
  useEffect(() => {
    // Add old body class if needed or keep it clean
    document.body.style.backgroundColor = 'var(--bg-space)';
    document.body.style.color = 'var(--ink-light)';
    document.body.style.fontFamily = "'Inter', sans-serif";
  }, []);

  useEffect(() => {
    setIsProfileOpen(false);
    setMobileNavOpen(false);
  }, [location.pathname]);

  const handleLogout = async () => {
    await signOut();
    setIsProfileOpen(false);
    navigate('/');
  };

  const submitAuth = async (event: React.FormEvent) => {
    event.preventDefault();
    setAuthBusy(true);
    setAuthError('');
    try {
      if (authMode === 'sign-up') {
        await signUp(authForm.email, authForm.password, authForm.fullName);
      } else {
        await signIn(authForm.email, authForm.password);
      }
      setAuthOpen(false);
      setAuthForm({ email: '', password: '', fullName: '' });
    } catch (error: any) {
      setAuthError(error.message || 'Authentication failed.');
    } finally {
      setAuthBusy(false);
    }
  };

  return (
    <div className={`shell ${isCommunityWorkspace ? 'community-app-shell' : ''}`} id="main-app">
      {!isCommunityWorkspace && (
        <nav className="global-navbar" aria-label="Main Navigation">
          <div className="logo-text">
            <Link to="/" style={{ textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center' }}>
              <img src="/ganesha.png" alt="Ganesha Logo" className="navbar-ganesha" /> 
              Shree Lakshmi <span className="highlight">Astro</span>
            </Link>
          </div>
          <div className="nav-links" id="desktop-navigation">
            {navItems.map((item) => (
              item.external ? (
                <a
                  key={item.to}
                  href={item.to}
                  target={item.targetBlank ? '_blank' : undefined}
                  rel={item.targetBlank ? 'noreferrer' : undefined}
                  className={`nav-btn ${location.pathname === item.to ? 'active' : ''}`}
                  style={{ textDecoration: 'none' }}
                >
                  {item.label}
                </a>
              ) : (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`nav-btn ${location.pathname === item.to ? 'active' : ''}`}
                  style={{ textDecoration: 'none' }}
                >
                  {item.label}
                </Link>
              )
            ))}
          </div>
          <div className="nav-auth">
            {loading ? (
              <span className="nav-btn">...</span>
            ) : isSignedIn ? (
              <div className="profile-menu-wrap">
                <button
                  type="button"
                  className="profile-avatar-trigger"
                  aria-label="Open profile menu"
                  aria-expanded={isProfileOpen}
                  onClick={() => setIsProfileOpen((open) => !open)}
                >
                  {profileInitial}
                </button>
                {isProfileOpen && (
                  <div className="profile-dropdown" role="menu">
                    <button type="button" className="profile-dropdown-item" role="menuitem" onClick={() => setIsProfileOpen(false)}>
                      <User size={17} />
                      <span>{session?.user?.email || 'Signed in'}</span>
                    </button>
                    <button type="button" className="profile-dropdown-item" role="menuitem" onClick={handleLogout}>
                      <LogOut size={17} />
                      <span>Log out</span>
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button type="button" id="btn-login-header" className="nav-btn" onClick={() => setAuthOpen(true)}>Sign In</button>
            )}
            <button
              type="button"
              className="nav-menu-toggle"
              aria-label={mobileNavOpen ? 'Close navigation menu' : 'Open navigation menu'}
              aria-expanded={mobileNavOpen}
              aria-controls="mobile-navigation"
              onClick={() => setMobileNavOpen((open) => !open)}
            >
              {mobileNavOpen ? <X size={20} /> : <Menu size={20} />}
            </button>
          </div>
        </nav>
      )}

      {!isCommunityWorkspace && mobileNavOpen && (
        <div className="mobile-nav-panel" id="mobile-navigation">
          {navItems.map((item) => (
            item.external ? (
              <a
                key={item.to}
                href={item.to}
                target={item.targetBlank ? '_blank' : undefined}
                rel={item.targetBlank ? 'noreferrer' : undefined}
                className={`mobile-nav-link ${location.pathname === item.to ? 'active' : ''}`}
              >
                {item.label}
              </a>
            ) : (
              <Link
                key={item.to}
                to={item.to}
                className={`mobile-nav-link ${location.pathname === item.to ? 'active' : ''}`}
              >
                {item.label}
              </Link>
            )
          ))}
        </div>
      )}

      {/* Main Content Area */}
      <div
        className={isCommunityWorkspace ? 'community-layout-host' : isHome ? '' : 'app-content-shell'}
      >
        <Outlet />
      </div>

      {!isCommunityWorkspace && (
        <footer className="app-footer react-legal-footer" aria-label="Website footer">
          <div className="footer-grid">
            <section className="footer-col about-col">
              <div className="footer-logo">
                <div className="logo-brush">
                  <span className="logo-text-top">Shree Lakshmi</span>
                  <span className="logo-text-bottom">Astro</span>
                </div>
              </div>
              <h3>ABOUT US</h3>
              <p>
                Shree Lakshmi Astro provides Research-Level Vedic Astrology
                Consultations & Predictions. Get Expert Vedic guidance on Career,
                Health, Relationships & more.
              </p>
            </section>
            <section className="footer-col links-col">
              <h3>QUICK LINKS</h3>
              <ul className="quick-links-list">
                <li><a href="/community/apply">Shree Lakshmi Astro Community (Astrologers)</a></li>
                {policyItems.map((item) => (
                  <li key={item.to}><a href={item.to}>{item.label}</a></li>
                ))}
              </ul>

              <h3 className="social-title">SOCIAL CHANNELS</h3>
              <div className="social-channels">
                <a href="#" className="social-icon" title="Instagram" aria-label="Instagram">IG</a>
                <a href="#" className="social-icon" title="Facebook" aria-label="Facebook">FB</a>
                <a href="#" className="social-icon" title="Twitter" aria-label="Twitter">X</a>
                <a href="#" className="social-icon" title="YouTube" aria-label="YouTube">YT</a>
              </div>
            </section>
            <section className="footer-col community-col">
              <p className="community-text">
                Join Shree Lakshmi Astro's WhatsApp for daily astrology insights.
                Enhance your success with our expert predictions.
              </p>
              <a
                href="https://whatsapp.com/channel/0029Vb8ZvHsKbYMLie7XIk0A"
                target="_blank"
                rel="noreferrer"
                className="btn-whatsapp-community"
              >
                <MessageCircle className="wa-icon" size={22} />
                <span>Join WhatsApp Community</span>
              </a>
            </section>
          </div>
          <div className="footer-bottom">
            <p>© 2026 Shree Lakshmi Astro. All Rights Reserved</p>
          </div>
        </footer>
      )}

      {authOpen && (
        <div className="auth-backdrop" role="presentation" onClick={() => setAuthOpen(false)}>
          <form className="auth-panel" onSubmit={submitAuth} onClick={(event) => event.stopPropagation()}>
            <button type="button" className="btn-close-auth" onClick={() => setAuthOpen(false)} aria-label="Close sign in">×</button>
            <h1>{authMode === 'sign-up' ? 'Create account' : 'Sign in'}</h1>
            <p>{authMode === 'sign-up' ? 'Create your Shree Lakshmi Astro account.' : 'Use your Shree Lakshmi Astro account.'}</p>
            {authError && <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm">{authError}</div>}
            {authMode === 'sign-up' && (
              <input
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900"
                placeholder="Full name"
                value={authForm.fullName}
                onChange={(event) => setAuthForm({ ...authForm, fullName: event.target.value })}
                required
              />
            )}
            <input
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900"
              type="email"
              placeholder="Email"
              value={authForm.email}
              onChange={(event) => setAuthForm({ ...authForm, email: event.target.value })}
              required
            />
            <input
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-gray-900"
              type="password"
              placeholder="Password"
              minLength={6}
              value={authForm.password}
              onChange={(event) => setAuthForm({ ...authForm, password: event.target.value })}
              required
            />
            <button type="submit" className="nav-btn" disabled={authBusy}>
              {authBusy ? 'Please wait...' : authMode === 'sign-up' ? 'Create account' : 'Sign in'}
            </button>
            <button
              type="button"
              className="profile-dropdown-item"
              onClick={() => {
                setAuthError('');
                setAuthMode(authMode === 'sign-up' ? 'sign-in' : 'sign-up');
              }}
            >
              {authMode === 'sign-up' ? 'I already have an account' : 'Create a new account'}
            </button>
          </form>
        </div>
      )}
    </div>
  );
};

export default Layout;
