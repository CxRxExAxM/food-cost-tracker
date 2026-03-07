import { Link } from 'react-router-dom';
import Navigation from '../components/Navigation';
import './Home.css';

function Home() {
  return (
    <div className="home">
      <Navigation />
      <div className="home-container">
        <header className="home-header">
          <h1>Food Costing</h1>
          <p>Manage distributor prices, map products, and calculate recipe costs</p>
        </header>

        <div className="nav-cards">
          <Link to="/products" className="nav-card">
            <div className="card-icon">📦</div>
            <h2>Products</h2>
            <p>View and map distributor products to common ingredients</p>
            <span className="card-arrow">&rarr;</span>
          </Link>

          <Link to="/recipes" className="nav-card">
            <div className="card-icon">📝</div>
            <h2>Recipes</h2>
            <p>Create recipes and calculate costs based on current prices</p>
            <span className="card-arrow">&rarr;</span>
          </Link>

          <Link to="/banquet-menus" className="nav-card">
            <div className="card-icon">🍽️</div>
            <h2>Banquet Menus</h2>
            <p>Build banquet menus with cost analysis per guest</p>
            <span className="card-arrow">&rarr;</span>
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
