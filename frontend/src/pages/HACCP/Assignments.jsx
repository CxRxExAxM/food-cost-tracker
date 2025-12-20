import Navigation from '../../components/Navigation';
import './HACCP.css';

function Assignments() {
  return (
    <div className="haccp-page">
      <Navigation />
      <div className="haccp-container">
        <header className="haccp-header">
          <h1>Checklist Assignments</h1>
          <button className="btn btn-primary">+ New Assignment</button>
        </header>

        <div className="assignments-content">
          <p className="coming-soon">Assignments interface coming soon...</p>
        </div>
      </div>
    </div>
  );
}

export default Assignments;
