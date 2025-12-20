import { Link } from 'react-router-dom';
import Navigation from '../../components/Navigation';
import { mockChecklists } from './mockData';
import './HACCP.css';

function Checklists() {
  return (
    <div className="haccp-page">
      <Navigation />
      <div className="haccp-container">
        <header className="haccp-header">
          <h1>Checklists</h1>
          <div className="header-actions">
            <Link to="/haccp/checklists/new" className="btn btn-primary">
              + New Checklist
            </Link>
          </div>
        </header>

        <div className="checklists-grid">
          {mockChecklists.map(checklist => (
            <div key={checklist.id} className="checklist-card">
              <div className="checklist-header">
                <h3>{checklist.name}</h3>
                <div className="checklist-tags">
                  {checklist.record_tags.map((tag, index) => (
                    <span key={index} className="tag">{tag}</span>
                  ))}
                </div>
              </div>
              <p className="checklist-description">{checklist.description}</p>
              <div className="checklist-meta">
                <span>{checklist.checks.length} checks</span>
              </div>
              <div className="checklist-actions">
                <Link to={`/haccp/checklists/${checklist.id}/edit`} className="btn btn-secondary btn-small">
                  Edit
                </Link>
                <button className="btn btn-tertiary btn-small">Delete</button>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Checklists;
