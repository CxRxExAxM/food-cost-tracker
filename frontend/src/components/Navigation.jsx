import { useState, useRef, useEffect, useMemo } from 'react';
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

  // Determine current module based on route
  const currentModule = useMemo(() => {
    const path = location.pathname;

    // HACCP module routes
    if (path.startsWith('/haccp')) {
      return 'HACCP Compliance';
    }

    // Food Cost module routes (existing features)
    if (path.startsWith('/food-cost') ||
        path === '/products' ||
        path === '/recipes') {
      return 'Food Cost Tracker';
    }

    // No module context for home, admin, super-admin, etc.
    return null;
  }, [location.pathname]);

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
              {currentModule && (
                <div className="brand-module">{currentModule}</div>
              )}
            </Link>
          </div>

          <div className="nav-links">
            <Link to="/" className={`nav-link ${isActivePath('/') ? 'active' : ''}`}>
              Home
            </Link>

            {/* Food Cost Module Links */}
            {currentModule === 'Food Cost Tracker' && (
              <>
                <Link to="/products" className={`nav-link ${isActivePath('/products') ? 'active' : ''}`}>
                  Products
                </Link>
                <Link to="/recipes" className={`nav-link ${isActivePath('/recipes') ? 'active' : ''}`}>
                  Recipes
                </Link>
              </>
            )}

            {/* HACCP Module Links */}
            {currentModule === 'HACCP Compliance' && (
              <>
                <Link to="/haccp" className={`nav-link ${isActivePath('/haccp') ? 'active' : ''}`}>
                  Dashboard
                </Link>
                <Link to="/haccp/checklists" className={`nav-link ${isActivePath('/haccp/checklists') || location.pathname.includes('/haccp/checklists/') ? 'active' : ''}`}>
                  Checklists
                </Link>
                <Link to="/haccp/assignments" className={`nav-link ${isActivePath('/haccp/assignments') ? 'active' : ''}`}>
                  Assignments
                </Link>
                <Link to="/haccp/reports" className={`nav-link ${isActivePath('/haccp/reports') ? 'active' : ''}`}>
                  Reports
                </Link>
              </>
            )}

            {/* Global Admin Links */}
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
            {user?.is_super_admin && (
              <Link to="/super-admin" className={`nav-link super-admin-link ${isActivePath('/super-admin') || isActivePath('/super-admin/organizations') ? 'active' : ''}`}>
                Super Admin
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
