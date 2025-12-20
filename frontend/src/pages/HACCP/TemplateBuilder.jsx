import Navigation from '../../components/Navigation';
import './HACCP.css';

function TemplateBuilder() {
  return (
    <div className="haccp-page">
      <Navigation />
      <div className="template-builder">
        <div className="builder-header">
          <h1>Template Builder</h1>
          <div className="builder-actions">
            <button className="btn btn-secondary">Cancel</button>
            <button className="btn btn-primary">Save Template</button>
          </div>
        </div>

        <div className="builder-content">
          {/* Check Type Library - Left Sidebar */}
          <div className="check-library">
            <h3>Check Types</h3>
            <p className="coming-soon">Building in progress...</p>
          </div>

          {/* Canvas - Center */}
          <div className="builder-canvas">
            <div className="template-form">
              <input
                type="text"
                placeholder="Template Name"
                className="input-large"
              />
              <textarea
                placeholder="Description"
                className="textarea"
                rows={3}
              />
            </div>
            <div className="checks-list">
              <p className="empty-state">Add checks from the library →</p>
            </div>
          </div>

          {/* Preview - Right Sidebar */}
          <div className="mobile-preview">
            <h3>Mobile Preview</h3>
            <div className="phone-frame">
              <p className="coming-soon">Preview will appear here</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TemplateBuilder;
