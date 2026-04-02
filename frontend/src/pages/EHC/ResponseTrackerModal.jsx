import { useState, useEffect } from 'react';
import { X, Trash2, Download, Check, Clock } from 'lucide-react';
import './ResponseTrackerModal.css';

const API_BASE = '/api/ehc';

function getAuthHeaders() {
  const token = localStorage.getItem('token');
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
}

/**
 * Modal for viewing and managing form responses
 */
export default function ResponseTrackerModal({
  isOpen,
  onClose,
  formLink,
  onResponseDeleted
}) {
  const [loading, setLoading] = useState(false);
  const [responses, setResponses] = useState([]);
  const [deletingId, setDeletingId] = useState(null);

  useEffect(() => {
    if (isOpen && formLink?.id) {
      loadResponses();
    }
  }, [isOpen, formLink?.id]);

  async function loadResponses() {
    try {
      setLoading(true);
      const response = await fetch(
        `${API_BASE}/form-links/${formLink.id}/responses`,
        { headers: getAuthHeaders() }
      );
      if (response.ok) {
        const data = await response.json();
        setResponses(data.data || []);
      }
    } catch (err) {
      console.error('Failed to load responses:', err);
    } finally {
      setLoading(false);
    }
  }

  async function deleteResponse(responseId) {
    if (!confirm('Remove this response? This cannot be undone.')) return;

    try {
      setDeletingId(responseId);
      const response = await fetch(
        `${API_BASE}/form-links/${formLink.id}/responses/${responseId}`,
        {
          method: 'DELETE',
          headers: getAuthHeaders()
        }
      );

      if (response.ok) {
        setResponses(responses.filter(r => r.id !== responseId));
        if (onResponseDeleted) {
          onResponseDeleted(responseId);
        }
      }
    } catch (err) {
      console.error('Failed to delete response:', err);
    } finally {
      setDeletingId(null);
    }
  }

  function formatDate(dateStr) {
    if (!dateStr) return '—';
    const date = new Date(dateStr);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  if (!isOpen || !formLink) return null;

  const progress = formLink.expected_responses
    ? Math.round((responses.length / formLink.expected_responses) * 100)
    : null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="response-tracker-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Responses</h2>
          <span className="modal-subtitle">{formLink.title}</span>
          <button className="modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-content">
          {/* Progress Summary */}
          <div className="progress-summary">
            <div className="progress-count">
              <span className="count-number">{responses.length}</span>
              {formLink.expected_responses && (
                <>
                  <span className="count-divider">/</span>
                  <span className="count-total">{formLink.expected_responses}</span>
                </>
              )}
              <span className="count-label">responses</span>
            </div>

            {progress !== null && (
              <div className="progress-bar-container">
                <div className="progress-bar">
                  <div
                    className="progress-fill"
                    style={{ width: `${Math.min(progress, 100)}%` }}
                  />
                </div>
                <span className="progress-pct">{progress}%</span>
              </div>
            )}

            {progress === 100 && (
              <div className="complete-badge">
                <Check size={16} />
                Complete
              </div>
            )}
          </div>

          {/* Response List */}
          {loading ? (
            <div className="loading-state">Loading responses...</div>
          ) : responses.length === 0 ? (
            <div className="empty-state">
              <Clock size={32} />
              <p>No responses yet</p>
              <span>Share the form link to collect signatures</span>
            </div>
          ) : (
            <div className="responses-list">
              {responses.map(resp => (
                <div key={resp.id} className="response-card">
                  <div className="response-main">
                    <div className="response-info">
                      <span className="respondent-name">{resp.respondent_name}</span>
                      {resp.respondent_role && (
                        <span className="respondent-role">{resp.respondent_role}</span>
                      )}
                      {resp.respondent_dept && (
                        <span className="respondent-dept">{resp.respondent_dept}</span>
                      )}
                    </div>
                    <span className="response-date">{formatDate(resp.submitted_at)}</span>
                  </div>

                  {/* Signature Preview */}
                  {resp.signature_data && (
                    <div className="signature-preview">
                      <img
                        src={resp.signature_data.startsWith('data:')
                          ? resp.signature_data
                          : `data:image/png;base64,${resp.signature_data}`}
                        alt={`Signature of ${resp.respondent_name}`}
                      />
                    </div>
                  )}

                  <div className="response-actions">
                    <button
                      className="btn-delete"
                      onClick={() => deleteResponse(resp.id)}
                      disabled={deletingId === resp.id}
                      title="Remove response"
                    >
                      <Trash2 size={14} />
                      {deletingId === resp.id ? 'Removing...' : 'Remove'}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="modal-footer">
          <span className="footer-hint">
            {responses.length} total • Last updated just now
          </span>
          <button className="btn-ghost" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
