import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Navigation from '../../components/Navigation';
import { mockInstances, mockTemplates } from './mockData';
import './HACCP.css';

function MobileCompletion() {
  const { instanceId } = useParams();
  const navigate = useNavigate();

  const [instance, setInstance] = useState(null);
  const [template, setTemplate] = useState(null);
  const [currentCheckIndex, setCurrentCheckIndex] = useState(0);
  const [results, setResults] = useState({});

  // Load instance and template data
  useEffect(() => {
    const foundInstance = mockInstances.find(i => i.id === parseInt(instanceId));
    if (foundInstance) {
      setInstance(foundInstance);
      const foundTemplate = mockTemplates.find(t => t.id === foundInstance.template_id);
      setTemplate(foundTemplate);

      // Initialize results object
      const initialResults = {};
      foundTemplate?.checks.forEach(check => {
        initialResults[check.id] = {
          value: null,
          requiresCorrectiveAction: false,
          correctiveActionNotes: ''
        };
      });
      setResults(initialResults);
    }
  }, [instanceId]);

  if (!instance || !template) {
    return (
      <div className="haccp-page">
        <Navigation />
        <div className="mobile-completion">
          <p className="coming-soon">Loading checklist...</p>
        </div>
      </div>
    );
  }

  const currentCheck = template.checks[currentCheckIndex];
  const isFirstCheck = currentCheckIndex === 0;
  const isLastCheck = currentCheckIndex === template.checks.length - 1;

  // Navigation handlers
  const handleNext = () => {
    if (!isLastCheck) {
      setCurrentCheckIndex(currentCheckIndex + 1);
    }
  };

  const handlePrevious = () => {
    if (!isFirstCheck) {
      setCurrentCheckIndex(currentCheckIndex - 1);
    }
  };

  // Result handlers
  const updateResult = (checkId, field, value) => {
    setResults({
      ...results,
      [checkId]: {
        ...results[checkId],
        [field]: value
      }
    });
  };

  // Check if current check result passes threshold
  const checkPassesThreshold = (check, value) => {
    if (check.check_type === 'cooler_temp' && value !== null && value !== '') {
      const threshold = check.config.threshold;
      const temp = parseFloat(value);

      if (check.config.comparison === 'less_than') {
        return temp < threshold;
      } else {
        return temp > threshold;
      }
    }

    if (check.check_type === 'thermometer_cal' && results[check.id]?.ice_water !== null && results[check.id]?.boiling_water !== null) {
      const iceWater = parseFloat(results[check.id].ice_water || 0);
      const boilingWater = parseFloat(results[check.id].boiling_water || 0);

      return iceWater <= 33 && boilingWater >= 210;
    }

    return true;
  };

  // Submit handler
  const handleSubmit = () => {
    console.log('Submitting checklist completion:', {
      instance_id: instance.id,
      template_id: template.id,
      template_name: template.name,
      outlet: instance.outlet_name,
      results: results
    });

    alert(`Checklist completed!\n\nResults logged to console (Demo mode - not persisted)\n\nTemplate: ${template.name}\nOutlet: ${instance.outlet_name}\nChecks completed: ${template.checks.length}`);

    navigate('/haccp');
  };

  // Render input based on check type
  const renderCheckInput = () => {
    const checkIcon = {
      'task': '✓',
      'cooler_temp': '🌡️',
      'thermometer_cal': '🔧',
      'meeting_notes': '📝'
    }[currentCheck.check_type] || '✓';

    const result = results[currentCheck.id];
    const passes = checkPassesThreshold(currentCheck, result?.value);

    return (
      <div className="check-completion">
        <div className="check-completion-icon">{checkIcon}</div>

        <div className="check-completion-header">
          <h2>{currentCheck.name}</h2>
          {currentCheck.description && (
            <p className="check-description">{currentCheck.description}</p>
          )}
        </div>

        <div className="check-completion-input">
          {/* Task - Simple checkbox */}
          {currentCheck.check_type === 'task' && (
            <label className="completion-checkbox-large">
              <input
                type="checkbox"
                checked={result?.value || false}
                onChange={(e) => updateResult(currentCheck.id, 'value', e.target.checked)}
              />
              <span>Task Completed</span>
            </label>
          )}

          {/* Cooler Temperature - Number input with threshold */}
          {currentCheck.check_type === 'cooler_temp' && (
            <div className="temperature-input">
              <label>Temperature Reading</label>
              <div className="temp-input-group">
                <input
                  type="number"
                  step="0.1"
                  placeholder="Enter temperature"
                  value={result?.value || ''}
                  onChange={(e) => updateResult(currentCheck.id, 'value', e.target.value)}
                  className="input-temperature"
                />
                <span className="temp-unit">{currentCheck.config.unit}</span>
              </div>

              {result?.value !== null && result?.value !== '' && (
                <div className={`threshold-indicator ${passes ? 'pass' : 'fail'}`}>
                  {passes ? '✓' : '✗'} Must be {currentCheck.config.comparison === 'less_than' ? 'less than' : 'greater than'} {currentCheck.config.threshold}{currentCheck.config.unit}
                </div>
              )}

              {!passes && result?.value !== null && result?.value !== '' && (
                <div className="corrective-action-section">
                  <label className="corrective-action-label">
                    <input
                      type="checkbox"
                      checked={result?.requiresCorrectiveAction || false}
                      onChange={(e) => updateResult(currentCheck.id, 'requiresCorrectiveAction', e.target.checked)}
                    />
                    <span>Corrective action required</span>
                  </label>

                  {result?.requiresCorrectiveAction && (
                    <textarea
                      placeholder="Describe corrective action taken..."
                      className="corrective-action-notes"
                      rows={4}
                      value={result?.correctiveActionNotes || ''}
                      onChange={(e) => updateResult(currentCheck.id, 'correctiveActionNotes', e.target.value)}
                    />
                  )}
                </div>
              )}
            </div>
          )}

          {/* Thermometer Calibration - Ice and boiling water tests */}
          {currentCheck.check_type === 'thermometer_cal' && (
            <div className="thermometer-cal-input">
              <div className="cal-test">
                <label>Ice Water Test (Should be ≤ 33°F)</label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="Temperature"
                  value={result?.ice_water || ''}
                  onChange={(e) => {
                    setResults({
                      ...results,
                      [currentCheck.id]: {
                        ...results[currentCheck.id],
                        ice_water: e.target.value
                      }
                    });
                  }}
                  className="input-temperature"
                />
              </div>

              <div className="cal-test">
                <label>Boiling Water Test (Should be ≥ 210°F)</label>
                <input
                  type="number"
                  step="0.1"
                  placeholder="Temperature"
                  value={result?.boiling_water || ''}
                  onChange={(e) => {
                    setResults({
                      ...results,
                      [currentCheck.id]: {
                        ...results[currentCheck.id],
                        boiling_water: e.target.value
                      }
                    });
                  }}
                  className="input-temperature"
                />
              </div>

              {result?.ice_water && result?.boiling_water && (
                <div className={`threshold-indicator ${passes ? 'pass' : 'fail'}`}>
                  {passes ? '✓ Calibration passed' : '✗ Calibration failed - thermometer needs adjustment'}
                </div>
              )}
            </div>
          )}

          {/* Meeting Notes - File upload simulation */}
          {currentCheck.check_type === 'meeting_notes' && (
            <div className="meeting-notes-input">
              {currentCheck.config.requires_file_upload && (
                <div className="file-upload-section">
                  <label>Upload Meeting Notes</label>
                  <button className="upload-btn">
                    📎 Choose File
                  </button>
                  <p className="upload-hint">PDF, DOC, or image files accepted</p>
                </div>
              )}

              {currentCheck.config.requires_attendance && (
                <div className="attendance-section">
                  <label className="completion-checkbox-large">
                    <input
                      type="checkbox"
                      checked={result?.attendance_tracked || false}
                      onChange={(e) => {
                        setResults({
                          ...results,
                          [currentCheck.id]: {
                            ...results[currentCheck.id],
                            attendance_tracked: e.target.checked
                          }
                        });
                      }}
                    />
                    <span>Attendance Recorded</span>
                  </label>
                </div>
              )}

              <textarea
                placeholder="Additional notes..."
                className="meeting-notes-textarea"
                rows={4}
                value={result?.notes || ''}
                onChange={(e) => {
                  setResults({
                    ...results,
                    [currentCheck.id]: {
                      ...results[currentCheck.id],
                      notes: e.target.value
                    }
                  });
                }}
              />
            </div>
          )}
        </div>
      </div>
    );
  };

  return (
    <div className="haccp-page">
      <Navigation />
      <div className="mobile-completion">
        <div className="completion-header">
          <h1>{template.name}</h1>
          <div className="completion-meta">
            <span className="completion-outlet">{instance.outlet_name}</span>
            <span className="completion-progress">
              Check {currentCheckIndex + 1} of {template.checks.length}
            </span>
          </div>
        </div>

        <div className="completion-content">
          {renderCheckInput()}

          <div className="completion-navigation">
            <button
              className="btn btn-secondary"
              onClick={handlePrevious}
              disabled={isFirstCheck}
            >
              ← Previous
            </button>

            {!isLastCheck ? (
              <button className="btn btn-primary" onClick={handleNext}>
                Next →
              </button>
            ) : (
              <button className="btn btn-primary" onClick={handleSubmit}>
                Submit Checklist
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default MobileCompletion;
