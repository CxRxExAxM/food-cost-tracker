import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Home.css';

function Home() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="home">
      <div className="home-container">
        <header className="home-header">
          <div className="header-top">
            <div className="user-info">
              <span className="user-name">{user?.full_name || user?.username}</span>
              <span className={`user-role role-${user?.role}`}>{user?.role}</span>
            </div>
            <button className="btn-logout" onClick={handleLogout}>
              Sign Out
            </button>
          </div>
          <h1>Food Cost Tracker</h1>
          <p>Manage distributor prices, map products, and calculate recipe costs</p>
        </header>

        <div className="nav-cards">
          <Link to="/products" className="nav-card">
            <div className="card-icon">📦</div>
            <h2>Products</h2>
            <p>View and map distributor products to common ingredients</p>
            <span className="card-arrow">-></span>
          </Link>

          <Link to="/recipes" className="nav-card">
            <div className="card-icon">📝</div>
            <h2>Recipes</h2>
            <p>Create recipes and calculate costs based on current prices</p>
            <span className="card-arrow">-></span>
          </Link>
        </div>

        <footer className="home-footer">
          <p>Select a section above to get started</p>
        </footer>
      </div>
    </div>
  );
}

export default Home;
