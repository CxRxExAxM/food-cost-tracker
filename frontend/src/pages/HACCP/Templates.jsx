import { Link } from 'react-router-dom';
import Navigation from '../../components/Navigation';
import { mockTemplates } from './mockData';
import './HACCP.css';

function Templates() {
  return (
    <div className="haccp-page">
      <Navigation />
      <div className="haccp-container">
        <header className="haccp-header">
          <h1>Checklist Templates</h1>
          <div className="header-actions">
            <Link to="/haccp/templates/new" className="btn btn-primary">
              + New Template
            </Link>
          </div>
        </header>

        <div className="templates-grid">
          {mockTemplates.map(template => (
            <div key={template.id} className="template-card">
              <div className="template-header">
                <h3>{template.name}</h3>
                <div className="template-tags">
                  {template.record_tags.map((tag, index) => (
                    <span key={index} className="tag">{tag}</span>
                  ))}
                </div>
              </div>
              <p className="template-description">{template.description}</p>
              <div className="template-meta">
                <span>{template.checks.length} checks</span>
              </div>
              <div className="template-actions">
                <Link to={`/haccp/templates/${template.id}/edit`} className="btn btn-secondary btn-small">
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

export default Templates;
