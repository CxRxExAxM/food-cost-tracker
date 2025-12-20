import { useState, useMemo } from 'react';
import Navigation from '../../components/Navigation';
import { mockInstances, mockResults, getResultsForInstance } from './mockData';
import './HACCP.css';

function Reports() {
  const [dateRange, setDateRange] = useState({
    start: '2024-12-01',
    end: '2024-12-31'
  });
  const [selectedInstance, setSelectedInstance] = useState(null);

  // Filter completed instances within date range
  const filteredInstances = useMemo(() => {
    return mockInstances.filter(instance => {
      if (instance.status !== 'completed') return false;

      const completedDate = new Date(instance.completed_at);
      const startDate = new Date(dateRange.start);
      const endDate = new Date(dateRange.end);

      return completedDate >= startDate && completedDate <= endDate;
    }).sort((a, b) => new Date(b.completed_at) - new Date(a.completed_at));
  }, [dateRange]);

  const handleViewDetails = (instance) => {
    setSelectedInstance(instance);
  };

  const handleCloseModal = () => {
    setSelectedInstance(null);
  };

  const handlePrint = () => {
    window.print();
  };

  const getStatusBadgeClass = (instance) => {
    if (instance.has_corrective_action) {
      return 'status-badge status-warning';
    }
    return 'status-badge status-success';
  };

  const getStatusText = (instance) => {
    if (instance.has_corrective_action) {
      return 'Completed (Action Taken)';
    }
    return 'Completed';
  };

  return (
    <div className="haccp-page">
      <Navigation />
      <div className="haccp-container">
        <header className="haccp-header">
          <h1>Compliance Reports</h1>
          <button className="btn btn-secondary no-print" onClick={handlePrint}>
            🖨 Print Report
          </button>
        </header>

        {/* Date Range Selector */}
        <div className="date-range-selector no-print">
          <div className="form-group">
            <label>Start Date</label>
            <input
              type="date"
              value={dateRange.start}
              onChange={(e) => setDateRange(prev => ({ ...prev, start: e.target.value }))}
              className="input-medium"
            />
          </div>
          <div className="form-group">
            <label>End Date</label>
            <input
              type="date"
              value={dateRange.end}
              onChange={(e) => setDateRange(prev => ({ ...prev, end: e.target.value }))}
              className="input-medium"
            />
          </div>
          <div className="date-range-summary">
            Showing {filteredInstances.length} completed checklist{filteredInstances.length !== 1 ? 's' : ''}
          </div>
        </div>

        {/* Reports Table */}
        <div className="reports-content">
          {filteredInstances.length === 0 ? (
            <div className="empty-state">
              <p>No completed checklists found for the selected date range.</p>
            </div>
          ) : (
            <div className="reports-table-container">
              <table className="reports-table">
                <thead>
                  <tr>
                    <th>Checklist</th>
                    <th>Outlet</th>
                    <th>Completed By</th>
                    <th>Completed Date</th>
                    <th>Status</th>
                    <th className="no-print">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredInstances.map(instance => (
                    <tr key={instance.id}>
                      <td>
                        <span className="checklist-name">{instance.checklist_name}</span>
                      </td>
                      <td>
                        <span className="outlet-badge">{instance.outlet_name}</span>
                      </td>
                      <td>{instance.completed_by}</td>
                      <td>
                        {new Date(instance.completed_at).toLocaleString('en-US', {
                          year: 'numeric',
                          month: 'short',
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}
                      </td>
                      <td>
                        <span className={getStatusBadgeClass(instance)}>
                          {getStatusText(instance)}
                        </span>
                      </td>
                      <td className="no-print">
                        <button
                          className="btn btn-small btn-secondary"
                          onClick={() => handleViewDetails(instance)}
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Detail Modal */}
        {selectedInstance && (
          <div className="modal-overlay no-print" onClick={handleCloseModal}>
            <div className="modal-content report-detail-modal" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <div>
                  <h2>{selectedInstance.checklist_name}</h2>
                  <p className="modal-subtitle">
                    {selectedInstance.outlet_name} • {new Date(selectedInstance.completed_at).toLocaleString()}
                  </p>
                </div>
                <button className="modal-close" onClick={handleCloseModal}>×</button>
              </div>

              <div className="modal-body">
                {/* Instance Info */}
                <div className="report-info-section">
                  <div className="report-info-item">
                    <span className="report-info-label">Completed By:</span>
                    <span className="report-info-value">{selectedInstance.completed_by}</span>
                  </div>
                  <div className="report-info-item">
                    <span className="report-info-label">Due Date:</span>
                    <span className="report-info-value">{new Date(selectedInstance.due_date).toLocaleDateString()}</span>
                  </div>
                  <div className="report-info-item">
                    <span className="report-info-label">Status:</span>
                    <span className={getStatusBadgeClass(selectedInstance)}>
                      {getStatusText(selectedInstance)}
                    </span>
                  </div>
                </div>

                {/* Check Results */}
                <div className="check-results-section">
                  <h3>Check Results</h3>
                  {getResultsForInstance(selectedInstance.id).map((result, idx) => (
                    <div
                      key={result.id}
                      className={`check-result-card ${result.requires_corrective_action ? 'check-result-failed' : 'check-result-passed'}`}
                    >
                      <div className="check-result-header">
                        <div className="check-result-title">
                          <span className="check-result-number">{idx + 1}.</span>
                          <span className="check-result-name">{result.check_name}</span>
                        </div>
                        <span className="check-result-status">
                          {result.requires_corrective_action ? '⚠ Failed' : '✓ Passed'}
                        </span>
                      </div>

                      <div className="check-result-body">
                        {/* Cooler Temp Results */}
                        {result.check_type === 'cooler_temp' && (
                          <div className="result-data">
                            <span className="result-label">Temperature:</span>
                            <span className={`result-value ${result.requires_corrective_action ? 'result-value-error' : ''}`}>
                              {result.result_data.temperature}°F
                            </span>
                          </div>
                        )}

                        {/* Task Results */}
                        {result.check_type === 'task' && (
                          <div className="result-data">
                            <span className="result-label">Status:</span>
                            <span className="result-value">
                              {result.result_data.completed ? 'Completed' : 'Not Completed'}
                            </span>
                          </div>
                        )}

                        {/* Corrective Action */}
                        {result.requires_corrective_action && result.corrective_action_notes && (
                          <div className="corrective-action-display">
                            <span className="corrective-action-label">Corrective Action Taken:</span>
                            <p className="corrective-action-text">{result.corrective_action_notes}</p>
                          </div>
                        )}

                        <div className="check-result-footer">
                          <span className="recorded-info">
                            Recorded by {result.recorded_by} at{' '}
                            {new Date(result.recorded_at).toLocaleString('en-US', {
                              hour: '2-digit',
                              minute: '2-digit'
                            })}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="modal-footer">
                <button className="btn btn-secondary" onClick={handleCloseModal}>
                  Close
                </button>
                <button className="btn btn-primary" onClick={handlePrint}>
                  Print Report
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default Reports;
