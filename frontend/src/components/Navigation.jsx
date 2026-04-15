import { useState, useRef, useEffect } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import OutletSelector from './outlets/OutletSelector';
import './Navigation.css';

function Navigation({ showModuleNav = true }) {
  const { user, logout, isAdmin } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const menuRef = useRef(null);

  // Determine current module based on path
  const isPotentialsModule = location.pathname.startsWith('/potentials');
  const isEHCModule = location.pathname.startsWith('/ehc');
  const isWasteModule = location.pathname.startsWith('/waste');
  const isDailyLogModule = location.pathname.startsWith('/daily-log');
  const isCostingModule = location.pathname.startsWith('/costing') ||
    location.pathname.startsWith('/products') ||
    location.pathname.startsWith('/recipes') ||
    location.pathname.startsWith('/banquet-menus') ||
    location.pathname.startsWith('/settings');
  const isAppLauncher = location.pathname === '/';

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

  const isSettingsActive = () => {
    return location.pathname.startsWith('/settings');
  };

  const organizationName = user?.organization_name || 'Organization';
  const organizationTier = user?.organization_tier || 'Free';

  // Determine module name for branding
  const getModuleName = () => {
    if (isPotentialsModule) return 'Potentials';
    if (isEHCModule) return 'EHC Compliance';
    if (isWasteModule) return 'Waste Tracking';
    if (isDailyLogModule) return 'Daily Logs';
    if (isCostingModule) return 'Food Costing';
    return null;
  };

  return (
    <nav className="navigation">
      <div className="nav-container">
        {/* Left: Branding + Nav Links */}
        <div className="nav-left">
          <div className="nav-brand">
            <Link to="/" className="brand-link">
              <div className="brand-name">RestauranTek</div>
              {getModuleName() && (
                <div className="brand-module">{getModuleName()}</div>
              )}
            </Link>
          </div>

          {showModuleNav && !isAppLauncher && (
            <div className="nav-links">
              {/* Apps link - always visible */}
              <Link to="/" className="nav-link apps-link">
                Apps
              </Link>

              {/* Settings link - always visible for admins */}
              {isAdmin() && (
                <Link to="/settings" className={`nav-link apps-link ${isSettingsActive() ? 'active' : ''}`}>
                  Settings
                </Link>
              )}

              {/* Costing module links */}
              {isCostingModule && (
                <>
                  <Link to="/costing" className={`nav-link ${isActivePath('/costing') ? 'active' : ''}`}>
                    Home
                  </Link>
                  <Link to="/products" className={`nav-link ${isActivePath('/products') ? 'active' : ''}`}>
                    Products
                  </Link>
                  <Link to="/recipes" className={`nav-link ${isActivePath('/recipes') ? 'active' : ''}`}>
                    Recipes
                  </Link>
                  <Link to="/banquet-menus" className={`nav-link ${isActivePath('/banquet-menus') ? 'active' : ''}`}>
                    Menus
                  </Link>
                </>
              )}

              {/* Potentials module - minimal nav since it's a single-page dashboard */}
              {isPotentialsModule && (
                <>
                  <Link to="/potentials" className={`nav-link ${isActivePath('/potentials') ? 'active' : ''}`}>
                    Dashboard
                  </Link>
                </>
              )}

              {/* EHC module - audit compliance tracking */}
              {isEHCModule && (
                <>
                  <Link to="/ehc" className={`nav-link ${isActivePath('/ehc') ? 'active' : ''}`}>
                    Dashboard
                  </Link>
                </>
              )}

              {/* Daily Log module - daily temperature monitoring */}
              {isDailyLogModule && (
                <>
                  <Link to="/daily-log" className={`nav-link ${isActivePath('/daily-log') ? 'active' : ''}`}>
                    Today
                  </Link>
                </>
              )}
            </div>
          )}
        </div>

        {/* Right: Org + User Info */}
        <div className="nav-right">
          <div className="org-badge">
            <span className="org-name">{organizationName}</span>
            <span className={getTierBadgeClass(organizationTier)}>
              {organizationTier}
            </span>
          </div>

          {/* Only show outlet selector in costing module */}
          {isCostingModule && <OutletSelector />}

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
