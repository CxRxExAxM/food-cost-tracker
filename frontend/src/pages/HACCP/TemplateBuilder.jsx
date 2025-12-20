import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Navigation from '../../components/Navigation';
import './HACCP.css';

// Available check types for the library
const CHECK_TYPES = [
  {
    type: 'task',
    name: 'Task',
    icon: '✓',
    description: 'Simple yes/no checklist item',
    defaultConfig: { result_type: 'boolean' }
  },
  {
    type: 'cooler_temp',
    name: 'Cooler Temperature',
    icon: '🌡️',
    description: 'Temperature reading with threshold',
    defaultConfig: { threshold: 38, unit: '°F', comparison: 'less_than' }
  },
  {
    type: 'monitored_cooler_temps',
    name: 'Monitored Cooler Temps',
    icon: '📡',
    description: 'IoT sensor readings in table view',
    defaultConfig: {
      sensor_ids: [],
      threshold_min: 32,
      threshold_max: 38,
      unit: '°F',
      verification_mode: 'exception_only'
    }
  },
  {
    type: 'thermometer_cal',
    name: 'Thermometer Calibration',
    icon: '🔧',
    description: 'Ice water and boiling water test',
    defaultConfig: {
      ice_water_threshold: 33,
      boiling_water_threshold: 210
    }
  },
  {
    type: 'meeting_notes',
    name: 'Meeting Notes',
    icon: '📝',
    description: 'File upload and attendance tracking',
    defaultConfig: {
      requires_file_upload: true,
      requires_attendance: true
    }
  }
];

function TemplateBuilder() {
  const navigate = useNavigate();
  const [templateName, setTemplateName] = useState('');
  const [description, setDescription] = useState('');
  const [checks, setChecks] = useState([]);
  const [draggedCheckType, setDraggedCheckType] = useState(null);
  const [draggedCheckIndex, setDraggedCheckIndex] = useState(null);

  // Handle dragging a check type from the library
  const handleCheckTypeDragStart = (checkType) => {
    setDraggedCheckType(checkType);
  };

  // Handle dropping a check type onto the canvas
  const handleCanvasDrop = (e) => {
    e.preventDefault();

    if (draggedCheckType) {
      // Add new check from library
      const newCheck = {
        id: Date.now(), // Temporary ID for demo
        check_type: draggedCheckType.type,
        name: draggedCheckType.name,
        description: '',
        order_index: checks.length + 1,
        config: { ...draggedCheckType.defaultConfig }
      };
      setChecks([...checks, newCheck]);
      setDraggedCheckType(null);
    } else if (draggedCheckIndex !== null) {
      // Reordering handled in handleCheckDrop
      setDraggedCheckIndex(null);
    }
  };

  const handleCanvasDragOver = (e) => {
    e.preventDefault();
  };

  // Handle dragging a check within the canvas for reordering
  const handleCheckDragStart = (index) => {
    setDraggedCheckIndex(index);
  };

  // Handle dropping a check to reorder
  const handleCheckDrop = (e, dropIndex) => {
    e.preventDefault();
    e.stopPropagation();

    if (draggedCheckIndex === null) return;

    const newChecks = [...checks];
    const draggedCheck = newChecks[draggedCheckIndex];

    // Remove from old position
    newChecks.splice(draggedCheckIndex, 1);

    // Insert at new position
    newChecks.splice(dropIndex, 0, draggedCheck);

    // Update order indices
    newChecks.forEach((check, index) => {
      check.order_index = index + 1;
    });

    setChecks(newChecks);
    setDraggedCheckIndex(null);
  };

  const handleCheckDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  // Remove a check from the list
  const handleRemoveCheck = (index) => {
    const newChecks = checks.filter((_, i) => i !== index);
    newChecks.forEach((check, i) => {
      check.order_index = i + 1;
    });
    setChecks(newChecks);
  };

  // Get icon for check type
  const getCheckIcon = (checkType) => {
    const type = CHECK_TYPES.find(t => t.type === checkType);
    return type?.icon || '✓';
  };

  // Handle save (mock for demo)
  const handleSave = () => {
    console.log('Saving template:', {
      name: templateName,
      description,
      checks
    });
    alert('Template saved! (Demo mode - not persisted)');
    navigate('/haccp/templates');
  };

  const handleCancel = () => {
    navigate('/haccp/templates');
  };

  return (
    <div className="haccp-page">
      <Navigation />
      <div className="template-builder">
        <div className="builder-header">
          <h1>Template Builder</h1>
          <div className="builder-actions">
            <button className="btn btn-secondary" onClick={handleCancel}>
              Cancel
            </button>
            <button
              className="btn btn-primary"
              onClick={handleSave}
              disabled={!templateName || checks.length === 0}
            >
              Save Template
            </button>
          </div>
        </div>

        <div className="builder-content">
          {/* Check Type Library - Left Sidebar */}
          <div className="check-library">
            <h3>Check Types</h3>
            <p className="library-hint">Drag to add →</p>
            <div className="check-type-list">
              {CHECK_TYPES.map((checkType) => (
                <div
                  key={checkType.type}
                  className="check-type-item"
                  draggable
                  onDragStart={() => handleCheckTypeDragStart(checkType)}
                >
                  <span className="check-type-icon">{checkType.icon}</span>
                  <div className="check-type-info">
                    <div className="check-type-name">{checkType.name}</div>
                    <div className="check-type-desc">{checkType.description}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Canvas - Center */}
          <div
            className="builder-canvas"
            onDrop={handleCanvasDrop}
            onDragOver={handleCanvasDragOver}
          >
            <div className="template-form">
              <input
                type="text"
                placeholder="Template Name"
                className="input-large"
                value={templateName}
                onChange={(e) => setTemplateName(e.target.value)}
              />
              <textarea
                placeholder="Description"
                className="textarea"
                rows={3}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </div>

            <div className="checks-list">
              {checks.length === 0 ? (
                <p className="empty-state">
                  Drag check types from the library to build your template
                </p>
              ) : (
                checks.map((check, index) => (
                  <div
                    key={check.id}
                    className="check-item"
                    draggable
                    onDragStart={() => handleCheckDragStart(index)}
                    onDrop={(e) => handleCheckDrop(e, index)}
                    onDragOver={handleCheckDragOver}
                  >
                    <span className="check-drag-handle">⋮⋮</span>
                    <span className="check-icon">{getCheckIcon(check.check_type)}</span>
                    <div className="check-details">
                      <div className="check-name">{check.name}</div>
                      <div className="check-type-label">{check.check_type.replace('_', ' ')}</div>
                    </div>
                    <button
                      className="check-remove"
                      onClick={() => handleRemoveCheck(index)}
                      title="Remove check"
                    >
                      ×
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Preview - Right Sidebar */}
          <div className="mobile-preview">
            <h3>Mobile Preview</h3>
            <div className="phone-frame">
              {checks.length === 0 ? (
                <div className="preview-empty">
                  <p>Add checks to see preview</p>
                </div>
              ) : (
                <div className="preview-content">
                  <div className="preview-header">
                    <h4>{templateName || 'Untitled Template'}</h4>
                    <span className="preview-progress">Check 1 of {checks.length}</span>
                  </div>
                  <div className="preview-check">
                    <div className="preview-check-icon">{getCheckIcon(checks[0].check_type)}</div>
                    <div className="preview-check-name">{checks[0].name}</div>
                    <div className="preview-check-type">{checks[0].check_type.replace('_', ' ')}</div>

                    {/* Simulated input based on check type */}
                    {checks[0].check_type === 'task' && (
                      <div className="preview-input">
                        <label className="preview-checkbox">
                          <input type="checkbox" />
                          <span>Completed</span>
                        </label>
                      </div>
                    )}

                    {checks[0].check_type === 'cooler_temp' && (
                      <div className="preview-input">
                        <label>Temperature</label>
                        <input type="number" placeholder="°F" />
                        <span className="preview-hint">Must be less than {checks[0].config.threshold}°F</span>
                      </div>
                    )}

                    {checks[0].check_type === 'thermometer_cal' && (
                      <div className="preview-input">
                        <label>Ice Water Test</label>
                        <input type="number" placeholder="°F" />
                        <label>Boiling Water Test</label>
                        <input type="number" placeholder="°F" />
                      </div>
                    )}

                    {checks[0].check_type === 'monitored_cooler_temps' && (
                      <div className="preview-input preview-sensor-table">
                        <div className="preview-sensor-row">
                          <span>Walk-in #1</span>
                          <span>36°F ✓</span>
                        </div>
                        <div className="preview-sensor-row">
                          <span>Bar Cooler</span>
                          <span>41°F ✗</span>
                        </div>
                        <div className="preview-hint">2 of 5 coolers shown</div>
                      </div>
                    )}

                    {checks[0].check_type === 'meeting_notes' && (
                      <div className="preview-input">
                        <button className="preview-upload-btn">📎 Upload File</button>
                        <label className="preview-checkbox">
                          <input type="checkbox" />
                          <span>Attendance tracked</span>
                        </label>
                      </div>
                    )}
                  </div>

                  <div className="preview-nav">
                    <button disabled>← Previous</button>
                    <button>Next →</button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default TemplateBuilder;
