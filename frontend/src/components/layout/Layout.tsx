import React, { useEffect } from 'react';
import { LogOut, User } from 'lucide-react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';

function getProfileInitial() {
  const token = localStorage.getItem('supabase_token');
  if (!token) return 'U';

  try {
    const payload = JSON.parse(atob(token.split('.')[1] || ''));
    const name = payload.user_metadata?.full_name || payload.user_metadata?.name || payload.email || payload.sub || 'User';
    return String(name).trim().charAt(0).toUpperCase() || 'U';
  } catch {
    return 'U';
  }
}

const Layout: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const isCommunityWorkspace = location.pathname === '/astro-community';
  const isHome = location.pathname === '/';
  const [isProfileOpen, setIsProfileOpen] = React.useState(false);
  const [profileInitial, setProfileInitial] = React.useState(getProfileInitial);
  const isSignedIn = Boolean(localStorage.getItem('supabase_token'));
  
  useEffect(() => {
    // Add old body class if needed or keep it clean
    document.body.style.backgroundColor = 'var(--bg-space)';
    document.body.style.color = 'var(--ink-light)';
    document.body.style.fontFamily = "'Inter', sans-serif";
  }, []);

  useEffect(() => {
    setIsProfileOpen(false);
    setProfileInitial(getProfileInitial());
  }, [location.pathname]);

  const handleLogout = () => {
    localStorage.removeItem('supabase_token');
    setIsProfileOpen(false);
    setProfileInitial('U');
    navigate('/');
  };

  return (
    <div className={`shell ${isCommunityWorkspace ? 'community-app-shell' : ''}`} id="main-app">
      {!isCommunityWorkspace && (
        <nav className="global-navbar" aria-label="Main Navigation">
          <div className="logo-text">
            <Link to="/" style={{ textDecoration: 'none', color: 'inherit', display: 'flex', alignItems: 'center' }}>
              <img src="/ganesha.png" alt="Ganesha Logo" className="navbar-ganesha" /> 
              ॐ <span className="highlight">Kundali</span> Studio
            </Link>
          </div>
          <div className="nav-links">
            <Link to="/" id="nav-home" className={`nav-btn ${location.pathname === '/' ? 'active' : ''}`} style={{ textDecoration: 'none' }}>Home</Link>
            <Link to="/booking" id="nav-consultant" className={`nav-btn ${location.pathname === '/booking' ? 'active' : ''}`} style={{ textDecoration: 'none' }}>Consultant</Link>
            <a href="/#pricing" id="nav-pricing" className="nav-btn" style={{ textDecoration: 'none' }}>Pricing</a>
            <a href="/frontend_old/about.html" id="nav-about" className="nav-btn" style={{ textDecoration: 'none' }}>About</a>
            <Link to="/astro-community" id="nav-community" className="nav-btn" style={{ textDecoration: 'none' }}>Astro Community</Link>
          </div>
          <div className="nav-auth">
            {isSignedIn ? (
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
                    <a href="/frontend_old/profile.html" className="profile-dropdown-item" role="menuitem" onClick={() => setIsProfileOpen(false)}>
                      <User size={17} />
                      <span>Profile</span>
                    </a>
                    <button type="button" className="profile-dropdown-item" role="menuitem" onClick={handleLogout}>
                      <LogOut size={17} />
                      <span>Log out</span>
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <button type="button" id="btn-login-header" className="nav-btn">Sign In</button>
            )}
          </div>
        </nav>
      )}

      {/* Main Content Area */}
      <div
        className={isCommunityWorkspace ? 'community-layout-host' : ''}
        style={isCommunityWorkspace || isHome ? undefined : { padding: '20px', maxWidth: '1200px', margin: '0 auto', width: '100%' }}
      >
        <Outlet />
      </div>
    </div>
  );
};

export default Layout;
