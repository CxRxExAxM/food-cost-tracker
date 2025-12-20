import { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import Navigation from '../../components/Navigation';
import { mockChecklists } from './mockData';
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

function ChecklistBuilder() {
  const navigate = useNavigate();
  const { id } = useParams();
  const [checklistName, setChecklistName] = useState('');
  const [description, setDescription] = useState('');
  const [checks, setChecks] = useState([]);
  const [draggedCheckType, setDraggedCheckType] = useState(null);
  const [draggedCheckIndex, setDraggedCheckIndex] = useState(null);
  const [editingCheck, setEditingCheck] = useState(null);
  const [editingCheckIndex, setEditingCheckIndex] = useState(null);

  // Load existing checklist data when editing
  useEffect(() => {
    if (id) {
      const checklist = mockChecklists.find(c => c.id === parseInt(id));
      if (checklist) {
        setChecklistName(checklist.name);
        setDescription(checklist.description || '');
        setChecks(checklist.checks || []);
      }
    }
  }, [id]);

  // Determine if we're in edit mode
  const isEditMode = !!id;

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

  // Open edit modal for a check
  const handleEditCheck = (index) => {
    setEditingCheckIndex(index);
    setEditingCheck({ ...checks[index] });
  };

  // Close edit modal
  const handleCloseEditModal = () => {
    setEditingCheck(null);
    setEditingCheckIndex(null);
  };

  // Save edited check
  const handleSaveCheckEdit = () => {
    if (editingCheckIndex !== null && editingCheck) {
      const newChecks = [...checks];
      newChecks[editingCheckIndex] = editingCheck;
      setChecks(newChecks);
      handleCloseEditModal();
    }
  };

  // Get icon for check type
  const getCheckIcon = (checkType) => {
    const type = CHECK_TYPES.find(t => t.type === checkType);
    return type?.icon || '✓';
  };

  // Handle save (mock for demo)
  const handleSave = () => {
    console.log(isEditMode ? 'Updating checklist:' : 'Creating new checklist:', {
      id: id ? parseInt(id) : null,
      name: checklistName,
      description,
      checks
    });
    alert(isEditMode ? 'Checklist updated! (Demo mode - not persisted)' : 'Checklist created! (Demo mode - not persisted)');
    navigate('/haccp/checklists');
  };

  const handleCancel = () => {
    navigate('/haccp/checklists');
  };

  return (
    <div className="haccp-page">
      <Navigation />
      <div className="checklist-builder">
        <div className="builder-header">
          <h1>{isEditMode ? 'Edit Checklist' : 'Checklist Builder'}</h1>
          <div className="builder-actions">
            <button className="btn btn-secondary" onClick={handleCancel}>
              Cancel
            </button>
            <button
              className="btn btn-primary"
              onClick={handleSave}
              disabled={!checklistName || checks.length === 0}
            >
              {isEditMode ? 'Update Checklist' : 'Save Checklist'}
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
            <div className="checklist-form">
              <input
                type="text"
                placeholder="Checklist Name"
                className="input-large"
                value={checklistName}
                onChange={(e) => setChecklistName(e.target.value)}
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
                  Drag check types from the library to build your checklist
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
                    <div className="check-actions">
                      <button
                        className="check-edit"
                        onClick={() => handleEditCheck(index)}
                        title="Edit check"
                      >
                        ✎
                      </button>
                      <button
                        className="check-remove"
                        onClick={() => handleRemoveCheck(index)}
                        title="Remove check"
                      >
                        ×
                      </button>
                    </div>
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
                    <h4>{checklistName || 'Untitled Checklist'}</h4>
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

        {/* Edit Check Modal */}
        {editingCheck && (
          <div className="modal-overlay" onClick={handleCloseEditModal}>
            <div className="modal-content check-edit-modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h2>Edit Check</h2>
                <button className="modal-close" onClick={handleCloseEditModal}>×</button>
              </div>

              <div className="modal-body">
                <div className="form-group">
                  <label>Check Name</label>
                  <input
                    type="text"
                    className="input-large"
                    value={editingCheck.name}
                    onChange={(e) => setEditingCheck({ ...editingCheck, name: e.target.value })}
                    placeholder="e.g., Walk-in Cooler #1"
                  />
                </div>

                <div className="form-group">
                  <label>Description (Optional)</label>
                  <textarea
                    className="textarea"
                    rows={2}
                    value={editingCheck.description || ''}
                    onChange={(e) => setEditingCheck({ ...editingCheck, description: e.target.value })}
                    placeholder="Additional details about this check"
                  />
                </div>

                {/* Configuration fields based on check type */}
                {editingCheck.check_type === 'cooler_temp' && (
                  <>
                    <div className="form-group">
                      <label>Temperature Threshold</label>
                      <div className="input-group">
                        <input
                          type="number"
                          step="0.1"
                          value={editingCheck.config.threshold}
                          onChange={(e) => setEditingCheck({
                            ...editingCheck,
                            config: { ...editingCheck.config, threshold: parseFloat(e.target.value) }
                          })}
                        />
                        <select
                          value={editingCheck.config.unit}
                          onChange={(e) => setEditingCheck({
                            ...editingCheck,
                            config: { ...editingCheck.config, unit: e.target.value }
                          })}
                        >
                          <option value="°F">°F</option>
                          <option value="°C">°C</option>
                        </select>
                      </div>
                    </div>

                    <div className="form-group">
                      <label>Comparison</label>
                      <select
                        className="input-large"
                        value={editingCheck.config.comparison}
                        onChange={(e) => setEditingCheck({
                          ...editingCheck,
                          config: { ...editingCheck.config, comparison: e.target.value }
                        })}
                      >
                        <option value="less_than">Must be less than</option>
                        <option value="greater_than">Must be greater than</option>
                      </select>
                    </div>
                  </>
                )}

                {editingCheck.check_type === 'thermometer_cal' && (
                  <>
                    <div className="form-group">
                      <label>Ice Water Threshold (°F)</label>
                      <input
                        type="number"
                        step="0.1"
                        className="input-large"
                        value={editingCheck.config.ice_water_threshold}
                        onChange={(e) => setEditingCheck({
                          ...editingCheck,
                          config: { ...editingCheck.config, ice_water_threshold: parseFloat(e.target.value) }
                        })}
                      />
                    </div>

                    <div className="form-group">
                      <label>Boiling Water Threshold (°F)</label>
                      <input
                        type="number"
                        step="0.1"
                        className="input-large"
                        value={editingCheck.config.boiling_water_threshold}
                        onChange={(e) => setEditingCheck({
                          ...editingCheck,
                          config: { ...editingCheck.config, boiling_water_threshold: parseFloat(e.target.value) }
                        })}
                      />
                    </div>
                  </>
                )}

                {editingCheck.check_type === 'meeting_notes' && (
                  <>
                    <div className="form-group">
                      <label className="checkbox-label">
                        <input
                          type="checkbox"
                          checked={editingCheck.config.requires_file_upload}
                          onChange={(e) => setEditingCheck({
                            ...editingCheck,
                            config: { ...editingCheck.config, requires_file_upload: e.target.checked }
                          })}
                        />
                        <span>Require file upload</span>
                      </label>
                    </div>

                    <div className="form-group">
                      <label className="checkbox-label">
                        <input
                          type="checkbox"
                          checked={editingCheck.config.requires_attendance}
                          onChange={(e) => setEditingCheck({
                            ...editingCheck,
                            config: { ...editingCheck.config, requires_attendance: e.target.checked }
                          })}
                        />
                        <span>Require attendance tracking</span>
                      </label>
                    </div>
                  </>
                )}
              </div>

              <div className="modal-footer">
                <button className="btn btn-secondary" onClick={handleCloseEditModal}>
                  Cancel
                </button>
                <button className="btn btn-primary" onClick={handleSaveCheckEdit}>
                  Save Changes
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ChecklistBuilder;
