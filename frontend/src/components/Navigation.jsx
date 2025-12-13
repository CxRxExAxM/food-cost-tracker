import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import OutletSelector from './outlets/OutletSelector';
import './Navigation.css';

function Navigation() {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef(null);

  // Close menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setShowUserMenu(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getTierBadgeClass = (tier) => {
    const tierLower = tier?.toLowerCase() || 'free';
    return `tier-badge tier-${tierLower}`;
  };

  const isActivePath = (path) => {
    return location.pathname === path;
  };

  // Get organization name from user object
  // Note: We'll need to add organization info to the user object from AuthContext
  const organizationName = user?.organization_name || 'Organization';
  const organizationTier = user?.organization_tier || 'Free';

  return (
    <nav className="navigation">
      <div className="nav-container">
        {/* Left: Branding + Nav Links */}
        <div className="nav-left">
          <div className="nav-brand">
            <Link to="/" className="brand-link">
              <div className="brand-name">RestauranTek</div>
              <div className="brand-module">Food Cost Tracker</div>
            </Link>
          </div>

          <div className="nav-links">
            <Link to="/" className={`nav-link ${isActivePath('/') ? 'active' : ''}`}>
              Home
            </Link>
            <Link to="/products" className={`nav-link ${isActivePath('/products') ? 'active' : ''}`}>
              Products
            </Link>
            <Link to="/recipes" className={`nav-link ${isActivePath('/recipes') ? 'active' : ''}`}>
              Recipes
            </Link>
            {isAdmin() && (
              <Link to="/users" className={`nav-link ${isActivePath('/users') ? 'active' : ''}`}>
                Users
              </Link>
            )}
            {isAdmin() && (
              <Link to="/outlets" className={`nav-link ${isActivePath('/outlets') ? 'active' : ''}`}>
                Outlets
              </Link>
            )}
            {isAdmin() && (
              <Link to="/admin" className={`nav-link ${isActivePath('/admin') ? 'active' : ''}`}>
                Admin
              </Link>
            )}
          </div>
        </div>

        {/* Right: Org + User Info */}
        <div className="nav-right">
          <div className="org-badge">
            <span className="org-name">{organizationName}</span>
            <span className={getTierBadgeClass(organizationTier)}>
              {organizationTier}
            </span>
          </div>

          <OutletSelector />

          <div className="user-menu" ref={menuRef}>
            <button
              className="user-menu-trigger"
              onClick={() => setShowUserMenu(!showUserMenu)}
            >
              <span className="user-name">{user?.full_name || user?.username}</span>
              <span className={`user-role role-${user?.role}`}>{user?.role}</span>
              <span className="user-menu-arrow">{showUserMenu ? '▲' : '▼'}</span>
            </button>

            {showUserMenu && (
              <div className="user-menu-dropdown">
                <div className="user-menu-header">
                  <div className="user-menu-name">{user?.full_name || user?.username}</div>
                  <div className="user-menu-email">{user?.email}</div>
                </div>
                <div className="user-menu-divider"></div>
                <button className="user-menu-item" onClick={handleLogout}>
                  <span className="user-menu-icon">🚪</span>
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navigation;
