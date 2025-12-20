import { useState } from 'react';
import Navigation from '../../components/Navigation';
import { mockAssignments, mockChecklists } from './mockData';
import './HACCP.css';

function Assignments() {
  const [showNewModal, setShowNewModal] = useState(false);
  const [newAssignment, setNewAssignment] = useState({
    checklist_id: '',
    outlet_id: '',
    assigned_to: [],
    recurrence: 'daily',
    recurrence_config: { time: '09:00' },
    start_date: new Date().toISOString().split('T')[0]
  });

  // Mock outlets data
  const mockOutlets = [
    { id: 1, name: "Downtown Kitchen" },
    { id: 2, name: "Westside Location" },
    { id: null, name: "All Outlets" }
  ];

  // Mock users data
  const mockUsers = [
    { id: 1, name: "John Smith" },
    { id: 2, name: "Sarah Chen" },
    { id: 3, name: "Mike Johnson" },
    { id: 4, name: "Emily Rodriguez" }
  ];

  const handleOpenNewModal = () => {
    setShowNewModal(true);
  };

  const handleCloseNewModal = () => {
    setShowNewModal(false);
    // Reset form
    setNewAssignment({
      checklist_id: '',
      outlet_id: '',
      assigned_to: [],
      recurrence: 'daily',
      recurrence_config: { time: '09:00' },
      start_date: new Date().toISOString().split('T')[0]
    });
  };

  const handleSaveAssignment = () => {
    console.log('New Assignment:', newAssignment);
    alert('Assignment created successfully! (Demo mode - not persisted)');
    handleCloseNewModal();
  };

  const handleUserToggle = (userName) => {
    setNewAssignment(prev => {
      const isSelected = prev.assigned_to.includes(userName);
      return {
        ...prev,
        assigned_to: isSelected
          ? prev.assigned_to.filter(u => u !== userName)
          : [...prev.assigned_to, userName]
      };
    });
  };

  const handleRecurrenceChange = (recurrence) => {
    let recurrence_config = {};
    if (recurrence === 'daily') {
      recurrence_config = { time: '09:00' };
    } else if (recurrence === 'weekly') {
      recurrence_config = { days: [1], time: '09:00' }; // Monday
    } else if (recurrence === 'monthly') {
      recurrence_config = { day: 1, time: '09:00' }; // 1st of month
    }

    setNewAssignment(prev => ({
      ...prev,
      recurrence,
      recurrence_config
    }));
  };

  const handleDeleteAssignment = (assignmentId) => {
    if (confirm('Are you sure you want to delete this assignment?')) {
      console.log('Delete assignment:', assignmentId);
      alert('Assignment deleted! (Demo mode - not persisted)');
    }
  };

  const getRecurrenceDisplay = (assignment) => {
    if (assignment.recurrence === 'daily') {
      return `Daily at ${assignment.recurrence_config.time}`;
    } else if (assignment.recurrence === 'weekly') {
      const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
      const dayNames = assignment.recurrence_config.days.map(d => days[d]).join(', ');
      return `Weekly on ${dayNames} at ${assignment.recurrence_config.time}`;
    } else if (assignment.recurrence === 'monthly') {
      return `Monthly on day ${assignment.recurrence_config.day} at ${assignment.recurrence_config.time}`;
    }
    return assignment.recurrence;
  };

  return (
    <div className="haccp-page">
      <Navigation />
      <div className="haccp-container">
        <header className="haccp-header">
          <h1>Checklist Assignments</h1>
          <button className="btn btn-primary" onClick={handleOpenNewModal}>
            + New Assignment
          </button>
        </header>

        <div className="assignments-content">
          <div className="assignments-table-container">
            <table className="assignments-table">
              <thead>
                <tr>
                  <th>Checklist</th>
                  <th>Outlet</th>
                  <th>Assigned To</th>
                  <th>Recurrence</th>
                  <th>Start Date</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {mockAssignments.map(assignment => (
                  <tr key={assignment.id}>
                    <td>
                      <div className="checklist-cell">
                        <span className="checklist-name">{assignment.checklist_name}</span>
                      </div>
                    </td>
                    <td>
                      <span className="outlet-badge">{assignment.outlet_name}</span>
                    </td>
                    <td>
                      <div className="assigned-users">
                        {assignment.assigned_to.map((user, idx) => (
                          <span key={idx} className="user-tag">{user}</span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <span className="recurrence-display">{getRecurrenceDisplay(assignment)}</span>
                    </td>
                    <td>{new Date(assignment.start_date).toLocaleDateString()}</td>
                    <td>
                      <div className="assignment-actions">
                        <button
                          className="btn-icon"
                          onClick={() => console.log('Edit assignment:', assignment.id)}
                          title="Edit"
                        >
                          ✎
                        </button>
                        <button
                          className="btn-icon btn-delete"
                          onClick={() => handleDeleteAssignment(assignment.id)}
                          title="Delete"
                        >
                          🗑
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* New Assignment Modal */}
        {showNewModal && (
          <div className="modal-overlay" onClick={handleCloseNewModal}>
            <div className="modal-content assignment-modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h2>New Assignment</h2>
                <button className="modal-close" onClick={handleCloseNewModal}>×</button>
              </div>

              <div className="modal-body">
                {/* Checklist Selector */}
                <div className="form-group">
                  <label>Checklist *</label>
                  <select
                    className="input-large"
                    value={newAssignment.checklist_id}
                    onChange={(e) => {
                      const checklistId = parseInt(e.target.value);
                      const checklist = mockChecklists.find(c => c.id === checklistId);
                      setNewAssignment(prev => ({
                        ...prev,
                        checklist_id: checklistId,
                        checklist_name: checklist?.name || ''
                      }));
                    }}
                  >
                    <option value="">Select a checklist...</option>
                    {mockChecklists.map(checklist => (
                      <option key={checklist.id} value={checklist.id}>
                        {checklist.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Outlet Selector */}
                <div className="form-group">
                  <label>Outlet *</label>
                  <select
                    className="input-large"
                    value={newAssignment.outlet_id === null ? 'all' : newAssignment.outlet_id}
                    onChange={(e) => {
                      const value = e.target.value;
                      const outlet = mockOutlets.find(o =>
                        value === 'all' ? o.id === null : o.id === parseInt(value)
                      );
                      setNewAssignment(prev => ({
                        ...prev,
                        outlet_id: value === 'all' ? null : parseInt(value),
                        outlet_name: outlet?.name || ''
                      }));
                    }}
                  >
                    <option value="">Select an outlet...</option>
                    {mockOutlets.map((outlet, idx) => (
                      <option key={idx} value={outlet.id === null ? 'all' : outlet.id}>
                        {outlet.name}
                      </option>
                    ))}
                  </select>
                </div>

                {/* User Multi-Select */}
                <div className="form-group">
                  <label>Assign To *</label>
                  <div className="user-checkbox-list">
                    {mockUsers.map(user => (
                      <label key={user.id} className="user-checkbox-item">
                        <input
                          type="checkbox"
                          checked={newAssignment.assigned_to.includes(user.name)}
                          onChange={() => handleUserToggle(user.name)}
                        />
                        <span>{user.name}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Recurrence Selector */}
                <div className="form-group">
                  <label>Recurrence *</label>
                  <select
                    className="input-large"
                    value={newAssignment.recurrence}
                    onChange={(e) => handleRecurrenceChange(e.target.value)}
                  >
                    <option value="daily">Daily</option>
                    <option value="weekly">Weekly</option>
                    <option value="monthly">Monthly</option>
                  </select>
                </div>

                {/* Recurrence Config Fields */}
                {newAssignment.recurrence === 'daily' && (
                  <div className="form-group">
                    <label>Time</label>
                    <input
                      type="time"
                      className="input-large"
                      value={newAssignment.recurrence_config.time}
                      onChange={(e) => setNewAssignment(prev => ({
                        ...prev,
                        recurrence_config: { time: e.target.value }
                      }))}
                    />
                  </div>
                )}

                {newAssignment.recurrence === 'weekly' && (
                  <>
                    <div className="form-group">
                      <label>Days of Week</label>
                      <div className="day-selector">
                        {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day, idx) => (
                          <label key={idx} className="day-checkbox">
                            <input
                              type="checkbox"
                              checked={newAssignment.recurrence_config.days.includes(idx)}
                              onChange={(e) => {
                                const days = e.target.checked
                                  ? [...newAssignment.recurrence_config.days, idx]
                                  : newAssignment.recurrence_config.days.filter(d => d !== idx);
                                setNewAssignment(prev => ({
                                  ...prev,
                                  recurrence_config: { ...prev.recurrence_config, days }
                                }));
                              }}
                            />
                            <span>{day}</span>
                          </label>
                        ))}
                      </div>
                    </div>
                    <div className="form-group">
                      <label>Time</label>
                      <input
                        type="time"
                        className="input-large"
                        value={newAssignment.recurrence_config.time}
                        onChange={(e) => setNewAssignment(prev => ({
                          ...prev,
                          recurrence_config: { ...prev.recurrence_config, time: e.target.value }
                        }))}
                      />
                    </div>
                  </>
                )}

                {newAssignment.recurrence === 'monthly' && (
                  <>
                    <div className="form-group">
                      <label>Day of Month</label>
                      <input
                        type="number"
                        className="input-large"
                        min="1"
                        max="31"
                        value={newAssignment.recurrence_config.day}
                        onChange={(e) => setNewAssignment(prev => ({
                          ...prev,
                          recurrence_config: { ...prev.recurrence_config, day: parseInt(e.target.value) }
                        }))}
                      />
                    </div>
                    <div className="form-group">
                      <label>Time</label>
                      <input
                        type="time"
                        className="input-large"
                        value={newAssignment.recurrence_config.time}
                        onChange={(e) => setNewAssignment(prev => ({
                          ...prev,
                          recurrence_config: { ...prev.recurrence_config, time: e.target.value }
                        }))}
                      />
                    </div>
                  </>
                )}

                {/* Start Date */}
                <div className="form-group">
                  <label>Start Date *</label>
                  <input
                    type="date"
                    className="input-large"
                    value={newAssignment.start_date}
                    onChange={(e) => setNewAssignment(prev => ({
                      ...prev,
                      start_date: e.target.value
                    }))}
                  />
                </div>

                {/* End Date (Optional) */}
                <div className="form-group">
                  <label>End Date (Optional)</label>
                  <input
                    type="date"
                    className="input-large"
                    value={newAssignment.end_date || ''}
                    onChange={(e) => setNewAssignment(prev => ({
                      ...prev,
                      end_date: e.target.value || null
                    }))}
                  />
                </div>
              </div>

              <div className="modal-footer">
                <button className="btn btn-secondary" onClick={handleCloseNewModal}>
                  Cancel
                </button>
                <button
                  className="btn btn-primary"
                  onClick={handleSaveAssignment}
                  disabled={
                    !newAssignment.checklist_id ||
                    newAssignment.outlet_id === '' ||
                    newAssignment.assigned_to.length === 0
                  }
                >
                  Create Assignment
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Assignments;
