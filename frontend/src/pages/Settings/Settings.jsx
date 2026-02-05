import { NavLink, Outlet, useLocation, Navigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import Navigation from '../../components/Navigation';
import { Users, Building2, Container, ArrowRightLeft, Settings as SettingsIcon, Shield } from 'lucide-react';
import './Settings.css';

function Settings() {
  const { isAdmin, user } = useAuth();
  const location = useLocation();

  // Redirect to first available tab if at /settings root
  if (location.pathname === '/settings') {
    return <Navigate to="/settings/users" replace />;
  }

  // Define tabs - filter based on permissions
  const tabs = [
    { path: 'users', label: 'Users', icon: Users, adminOnly: true },
    { path: 'outlets', label: 'Outlets', icon: Building2, adminOnly: true },
    { path: 'vessels', label: 'Vessels', icon: Container, adminOnly: true },
    { path: 'conversions', label: 'Conversions', icon: ArrowRightLeft, adminOnly: true },
    { path: 'admin', label: 'Admin', icon: SettingsIcon, adminOnly: true },
    { path: 'super-admin', label: 'Super Admin', icon: Shield, superAdminOnly: true },
  ];

  // Filter tabs based on user permissions
  const visibleTabs = tabs.filter(tab => {
    if (tab.superAdminOnly && !user?.is_super_admin) return false;
    if (tab.adminOnly && !isAdmin()) return false;
    return true;
  });

  return (
    <div className="settings-page">
      <Navigation />
      <div className="settings-layout">
        <aside className="settings-sidebar">
          <h2 className="settings-sidebar-title">Settings</h2>
          <nav className="settings-nav">
            {visibleTabs.map(tab => (
              <NavLink
                key={tab.path}
                to={`/settings/${tab.path}`}
                className={({ isActive }) =>
                  `settings-nav-link ${isActive ? 'active' : ''} ${tab.superAdminOnly ? 'super-admin' : ''}`
                }
              >
                <tab.icon size={18} />
                <span>{tab.label}</span>
              </NavLink>
            ))}
          </nav>
        </aside>
        <main className="settings-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default Settings;
