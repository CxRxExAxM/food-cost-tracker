import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Navigation from '../components/Navigation';
import { mockStats } from './HACCP/mockData';
import './Home.css';

function Home() {
  const { isAdmin } = useAuth();

  // For demo: hardcoded stats (will be from API in production)
  const foodCostStats = {
    recipesCount: 24,
    productsCount: 156
  };

  const haccpStats = mockStats;

  return (
    <div className="home">
      <Navigation />
      <div className="home-container">
        <header className="home-header">
          <h1>RestauranTek</h1>
          <p>Food Cost Management & HACCP Compliance Platform</p>
        </header>

        <div className="module-cards">
          {/* Food Cost Module Card */}
          <Link to="/products" className="module-card">
            <div className="module-icon">📊</div>
            <h2>Food Cost Tracker</h2>
            <p>Manage distributor products, map ingredients, and calculate recipe costs</p>
            <div className="module-stats">
              <span className="stat-badge">{foodCostStats.recipesCount} Recipes</span>
              <span className="stat-badge">{foodCostStats.productsCount} Products</span>
            </div>
            <button className="btn-enter-module">
              Enter Module <span className="module-arrow">→</span>
            </button>
          </Link>

          {/* HACCP Module Card */}
          <Link to="/haccp" className="module-card">
            <div className="module-icon">✓</div>
            <h2>HACCP Compliance</h2>
            <p>Checklists, temperature monitoring, and food safety documentation</p>
            <div className="module-stats">
              {haccpStats.dueToday > 0 && (
                <span className="stat-badge badge-yellow">{haccpStats.dueToday} Due Today</span>
              )}
              <span className="stat-badge badge-green">{haccpStats.completedThisWeek} Completed This Week</span>
            </div>
            <button className="btn-enter-module">
              Enter Module <span className="module-arrow">→</span>
            </button>
          </Link>
        </div>

        {/* Admin Quick Links */}
        {isAdmin() && (
          <div className="admin-quick-links">
            <h3>Administration</h3>
            <div className="quick-links-grid">
              <Link to="/users" className="quick-link">
                <span className="quick-link-icon">👥</span>
                <span className="quick-link-text">Users</span>
              </Link>
              <Link to="/outlets" className="quick-link">
                <span className="quick-link-icon">🏪</span>
                <span className="quick-link-text">Outlets</span>
              </Link>
              <Link to="/admin" className="quick-link">
                <span className="quick-link-icon">⚙️</span>
                <span className="quick-link-text">Settings</span>
              </Link>
            </div>
          </div>
        )}

        <footer className="home-footer">
          <p>Select a module above to get started</p>
        </footer>
      </div>
    </div>
  );
}

export default Home;
