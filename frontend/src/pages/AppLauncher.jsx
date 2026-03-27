import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import Navigation from '../components/Navigation';
import './AppLauncher.css';

function AppLauncher() {
  const { user } = useAuth();

  const modules = [
    {
      id: 'costing',
      name: 'Food Costing',
      description: 'Manage products, recipes, and banquet menus with real-time cost calculations',
      icon: '💰',
      path: '/costing',
      enabled: true,
      color: 'green'
    },
    {
      id: 'potentials',
      name: 'Potentials',
      description: 'F&B planning dashboard with forecasts, events, and group tracking',
      icon: '📊',
      path: '/potentials',
      enabled: true,
      color: 'blue'
    },
    {
      id: 'ehc',
      name: 'EHC Compliance',
      description: 'Environmental Health audit tracking and record management',
      icon: '📋',
      path: '/ehc',
      enabled: true,
      color: 'purple'
    },
    {
      id: 'haccp',
      name: 'HACCP',
      description: 'Food safety management and compliance tracking',
      icon: '🛡️',
      path: null,
      enabled: false,
      color: 'teal',
      badge: 'Coming Soon'
    }
  ];

  return (
    <div className="app-launcher">
      <Navigation showModuleNav={false} />
      <div className="launcher-container">
        <header className="launcher-header">
          <h1>RestauranTek</h1>
          <p>Select a module to get started</p>
        </header>

        <div className="module-grid">
          {modules.map((module) => (
            module.enabled ? (
              <Link
                key={module.id}
                to={module.path}
                className={`module-card module-${module.color}`}
              >
                <div className="module-icon">{module.icon}</div>
                <div className="module-content">
                  <h2>{module.name}</h2>
                  <p>{module.description}</p>
                </div>
                <span className="module-arrow">&rarr;</span>
              </Link>
            ) : (
              <div
                key={module.id}
                className={`module-card module-${module.color} module-disabled`}
              >
                <div className="module-icon">{module.icon}</div>
                <div className="module-content">
                  <h2>{module.name}</h2>
                  <p>{module.description}</p>
                </div>
                {module.badge && (
                  <span className="module-badge">{module.badge}</span>
                )}
              </div>
            )
          ))}
        </div>

        <footer className="launcher-footer">
          <p>Welcome back, {user?.full_name || user?.username}</p>
        </footer>
      </div>
    </div>
  );
}

export default AppLauncher;
