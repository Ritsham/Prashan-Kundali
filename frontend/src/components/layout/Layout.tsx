import React, { useEffect } from 'react';
import { LogOut, Menu, MessageCircle, User } from 'lucide-react';
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
  const { session, loading, signInWithGoogle, signOut } = useAuth();
  const isCommunityWorkspace = location.pathname === '/astro-community';
  const isHome = location.pathname === '/';
  const [isProfileOpen, setIsProfileOpen] = React.useState(false);
  const [authOpen, setAuthOpen] = React.useState(false);
  const [authMode, setAuthMode] = React.useState<'sign_in' | 'sign_up'>('sign_in');
  const [authError, setAuthError] = React.useState('');
  const [authBusy, setAuthBusy] = React.useState(false);
  const [signupForm, setSignupForm] = React.useState({ fullName: '', mobileNumber: '' });
  const [mobileNavOpen, setMobileNavOpen] = React.useState(false);
  const isSignedIn = Boolean(session?.access_token);
  const role = session?.user?.role || 'user';
  const canOpenCommunity = role === 'admin' || role === 'astrologer_verified';
  const desktopNavItems: NavItem[] = [
    { label: 'Home', to: '/index.html', external: true },
    { label: 'Consultant', to: '/consultation', external: true },
    { label: 'Payment', to: '/payment' },
    { label: 'Pricing', to: '/index.html#pricing', external: true },
    { label: 'About', to: '/about.html', external: true },
    ...(canOpenCommunity ? [{ label: 'Astro Community', to: '/astro-community' }] : []),
    ...(role === 'admin' ? [{ label: 'Admin', to: '/admin' }] : []),
  ];
  const mobileNavItems: NavItem[] = [
    { label: 'Home', to: '/index.html', external: true },
    { label: 'Consultant', to: '/consultation', external: true },
    { label: 'Astro Community', to: '/astro-community' },
    { label: 'Privacy Policy', to: '/privacy-policy.html', external: true },
    { label: 'Refund Policy', to: '/refund-policy.html', external: true },
    { label: 'Return Policy', to: '/return-policy.html', external: true },
    { label: 'About', to: '/about.html', external: true },
    { label: 'Contact Us', to: '/about-contact.html', external: true },
    ...(role === 'admin' ? [{ label: 'Admin', to: '/admin' }] : []),
  ];
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

  useEffect(() => {
    document.body.classList.toggle('react-mobile-nav-lock', mobileNavOpen);
    return () => document.body.classList.remove('react-mobile-nav-lock');
  }, [mobileNavOpen]);

  const handleLogout = async () => {
    await signOut();
    setIsProfileOpen(false);
    navigate('/');
  };

  const validMobileNumber = (mobileNumber: string) => /^\+?[0-9 ()-]{6,24}$/.test(mobileNumber);

  const startGoogleSignIn = async () => {
    setAuthBusy(true);
    setAuthError('');
    try {
      await signInWithGoogle('sign_in');
    } catch (error: any) {
      setAuthError(error.message || 'Google sign in failed.');
      setAuthBusy(false);
    }
  };

  const startGoogleSignUp = async (event: React.FormEvent) => {
    event.preventDefault();
    const fullName = signupForm.fullName.trim();
    const mobileNumber = signupForm.mobileNumber.trim();
    if (!fullName) {
      setAuthError('Please enter your full name.');
      return;
    }
    if (!validMobileNumber(mobileNumber)) {
      setAuthError('Please enter a valid mobile number.');
      return;
    }
    setAuthBusy(true);
    setAuthError('');
    try {
      await signInWithGoogle('sign_up', { fullName, mobileNumber });
    } catch (error: any) {
      setAuthError(error.message || 'Google sign up failed.');
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
            {desktopNavItems.map((item) => (
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
              <button
                type="button"
                id="btn-login-header"
                className="nav-btn"
                onClick={() => {
                  setAuthMode('sign_in');
                  setAuthOpen(true);
                }}
              >
                Sign In
              </button>
            )}
            <button
              type="button"
              className="nav-menu-toggle"
              aria-label="Open navigation menu"
              aria-expanded={mobileNavOpen}
              aria-controls="mobile-navigation"
              onClick={() => setMobileNavOpen((open) => !open)}
            >
              <Menu size={20} />
            </button>
          </div>
        </nav>
      )}

      {!isCommunityWorkspace && mobileNavOpen && (
        <>
          <button type="button" className="mobile-nav-scrim" aria-label="Close navigation menu" onClick={() => setMobileNavOpen(false)} />
          <div className="mobile-nav-panel" id="mobile-navigation">
            <button
              type="button"
              className="mobile-nav-account"
              onClick={() => {
                setMobileNavOpen(false);
                if (isSignedIn) window.location.href = '/profile.html';
                else {
                  setAuthMode('sign_in');
                  setAuthOpen(true);
                }
              }}
            >
              <span className="mobile-nav-account-avatar">{profileInitial}</span>
              <span className="mobile-nav-account-copy">
                <span className="mobile-nav-account-name">{isSignedIn ? session?.user?.email || 'Signed in' : 'Guest'}</span>
                <span className="mobile-nav-account-text">{isSignedIn ? 'Open your profile' : 'Sign in to save your charts'}</span>
              </span>
            </button>
            {mobileNavItems.map((item) => {
              const isActive = item.to.includes('consultation')
                ? location.pathname.includes('consultation')
                : item.to.includes('astro-community')
                  ? location.pathname.includes('astro-community')
                  : location.pathname === item.to;
              const className = `mobile-nav-link ${isActive ? 'active' : ''} ${item.label === 'Astro Community' ? 'mobile-nav-community' : ''}`;
              return item.external ? (
                <a
                  key={item.to}
                  href={item.to}
                  target={item.targetBlank ? '_blank' : undefined}
                  rel={item.targetBlank ? 'noreferrer' : undefined}
                  className={className}
                >
                  {item.label}
                  {item.label === 'Astro Community' && <span>(Astrologers Only)</span>}
                </a>
              ) : (
                <Link
                  key={item.to}
                  to={item.to}
                  className={className}
                  onClick={() => setMobileNavOpen(false)}
                >
                  {item.label}
                  {item.label === 'Astro Community' && <span>(Astrologers Only)</span>}
                </Link>
              );
            })}
          </div>
        </>
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
          <div className="auth-panel" role="dialog" aria-modal="true" aria-labelledby="google-auth-title" onClick={(event) => event.stopPropagation()}>
            <button type="button" className="btn-close-auth" onClick={() => setAuthOpen(false)} aria-label="Close sign in">×</button>
            <h1 id="google-auth-title">{authMode === 'sign_in' ? 'Sign in' : 'Sign up'}</h1>
            <div className="auth-mode-tabs" role="tablist" aria-label="Authentication options">
              <button
                type="button"
                className={authMode === 'sign_in' ? 'active' : ''}
                aria-selected={authMode === 'sign_in'}
                onClick={() => {
                  setAuthMode('sign_in');
                  setAuthError('');
                }}
              >
                Sign in
              </button>
              <button
                type="button"
                className={authMode === 'sign_up' ? 'active' : ''}
                aria-selected={authMode === 'sign_up'}
                onClick={() => {
                  setAuthMode('sign_up');
                  setAuthError('');
                }}
              >
                Sign up
              </button>
            </div>
            {authError && <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm">{authError}</div>}
            {authMode === 'sign_in' ? (
              <>
                <p>Use Google to continue with your existing account.</p>
                <button type="button" className="btn-google-login" disabled={authBusy} onClick={startGoogleSignIn}>
                  {authBusy ? 'Opening Google...' : 'Sign in with Google'}
                </button>
              </>
            ) : (
              <form className="auth-signup-form" onSubmit={startGoogleSignUp}>
                <p>Create your account once with name, mobile number, and Google.</p>
                <div className="auth-fields">
                  <label htmlFor="signup-full-name">Full name</label>
                  <input
                    id="signup-full-name"
                    type="text"
                    autoComplete="name"
                    maxLength={120}
                    value={signupForm.fullName}
                    onChange={(event) => setSignupForm({ ...signupForm, fullName: event.target.value })}
                    required
                  />
                  <label htmlFor="signup-mobile-number">Mobile number</label>
                  <input
                    id="signup-mobile-number"
                    type="tel"
                    autoComplete="tel"
                    maxLength={24}
                    placeholder="+91 98765 43210"
                    value={signupForm.mobileNumber}
                    onChange={(event) => setSignupForm({ ...signupForm, mobileNumber: event.target.value })}
                    required
                  />
                </div>
                <button type="submit" className="btn-google-login" disabled={authBusy}>
                  {authBusy ? 'Opening Google...' : 'Continue with Google'}
                </button>
              </form>
            )}
          </div>
        </div>
      )}

    </div>
  );
};

export default Layout;
