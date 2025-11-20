import { Link } from 'react-router-dom';
import './Recipes.css';

function Recipes() {
  return (
    <div className="container">
      <Link to="/" className="back-link">← Back to Home</Link>

      <div className="page-header">
        <h1>Recipes</h1>
        <p>Create and manage recipes with cost calculations</p>
      </div>

      <div className="coming-soon">
        <div className="coming-soon-icon">🚧</div>
        <h2>Coming Soon</h2>
        <p>Recipe management and cost calculation features are under development.</p>
      </div>
    </div>
  );
}

export default Recipes;
