/**
 * Forms Tab Component
 *
 * Admin workbench for digital form management:
 * - Create new forms from template gallery
 * - View all form links for the current cycle
 * - Track response progress
 * - Quick actions: QR, Flyer, Responses, Deactivate
 */

import { useState, useEffect } from 'react';
import {
  API_BASE,
  fetchWithAuth,
} from './shared';
import SimpleSignoffModal from '../modals/SimpleSignoffModal';
import StaffDeclarationModal from '../modals/StaffDeclarationModal';
import TeamRosterModal from '../modals/TeamRosterModal';
import TableSignoffModal from '../modals/TableSignoffModal';

export default function Forms({ activeCycle, toast }) {
  const [formLinks, setFormLinks] = useState([]);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [typeFilter, setTypeFilter] = useState('all');
  const [expandedLink, setExpandedLink] = useState(null);
  const [responses, setResponses] = useState({});
  const [loadingResponses, setLoadingResponses] = useState(null);
  const [deletingLink, setDeletingLink] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [editingLink, setEditingLink] = useState(null);
  const [editForm, setEditForm] = useState({ title: '', expected_responses: '' });
  const [saving, setSaving] = useState(false);

  // Modal state
  const [showSimpleSignoff, setShowSimpleSignoff] = useState(false);
  const [showStaffDeclaration, setShowStaffDeclaration] = useState(false);
  const [showTeamRoster, setShowTeamRoster] = useState(false);
  const [showTableSignoff, setShowTableSignoff] = useState(false);

  // Load form links and records when cycle changes
  useEffect(() => {
    if (activeCycle?.id) {
      loadFormLinks();
      loadRecords();
    }
  }, [activeCycle?.id]);

  async function loadFormLinks() {
    try {
      setLoading(true);
      const data = await fetchWithAuth(`${API_BASE}/cycles/${activeCycle.id}/form-links`);
      setFormLinks(data.data || []);
    } catch (error) {
      console.error('Failed to load form links:', error);
      toast?.error?.('Failed to load form links');
    } finally {
      setLoading(false);
    }
  }

  async function loadRecords() {
    try {
      const data = await fetchWithAuth(`${API_BASE}/cycles/${activeCycle.id}/records`);
      setRecords(data.data || []);
    } catch (error) {
      console.error('Failed to load records:', error);
    }
  }

  async function loadResponses(linkId) {
    if (responses[linkId]) return;
    try {
      setLoadingResponses(linkId);
      const data = await fetchWithAuth(`${API_BASE}/form-links/${linkId}/responses`);
      setResponses(prev => ({ ...prev, [linkId]: data.data || [] }));
    } catch (error) {
      console.error('Failed to load responses:', error);
      toast?.error?.('Failed to load responses');
    } finally {
      setLoadingResponses(null);
    }
  }

  async function toggleLinkActive(link) {
    try {
      await fetchWithAuth(`${API_BASE}/form-links/${link.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !link.is_active })
      });
      toast?.success?.(link.is_active ? 'Form link deactivated' : 'Form link reactivated');
      loadFormLinks();
    } catch (error) {
      toast?.error?.('Failed to update form link');
    }
  }

  async function deleteFormLink(link) {
    try {
      setDeletingLink(link.id);
      await fetchWithAuth(`${API_BASE}/form-links/${link.id}`, {
        method: 'DELETE'
      });
      toast?.success?.('Form link deleted');
      setConfirmDelete(null);
      setExpandedLink(null);
      loadFormLinks();
    } catch (error) {
      toast?.error?.('Failed to delete form link');
    } finally {
      setDeletingLink(null);
    }
  }

  function startEditing(link) {
    setEditingLink(link.id);
    setEditForm({
      title: link.title || '',
      expected_responses: link.expected_responses || ''
    });
  }

  function cancelEditing() {
    setEditingLink(null);
    setEditForm({ title: '', expected_responses: '' });
  }

  async function saveEdit(linkId) {
    try {
      setSaving(true);
      const payload = {
        title: editForm.title || null,
        expected_responses: editForm.expected_responses ? parseInt(editForm.expected_responses) : null
      };
      await fetchWithAuth(`${API_BASE}/form-links/${linkId}`, {
        method: 'PATCH',
        body: JSON.stringify(payload)
      });
      toast?.success?.('Form link updated');
      setEditingLink(null);
      loadFormLinks();
    } catch (error) {
      toast?.error?.('Failed to update form link');
    } finally {
      setSaving(false);
    }
  }

  async function downloadQR(link) {
    try {
      const response = await fetch(`/api/ehc/form-links/${link.id}/qr`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (!response.ok) throw new Error('Failed to download QR');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `QR_${link.record_number}_${link.form_type}.png`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      toast?.error?.('Failed to download QR code');
    }
  }

  async function downloadFlyer(link) {
    try {
      const response = await fetch(`/api/ehc/form-links/${link.id}/flyer`, {
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (!response.ok) throw new Error('Failed to download flyer');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `Flyer_${link.record_number}_${activeCycle.year}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      toast?.error?.('Failed to download flyer');
    }
  }

  async function downloadPDF(link) {
    try {
      const response = await fetch(`/api/ehc/form-links/${link.id}/generate-pdf`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
      });
      if (!response.ok) throw new Error('Failed to generate PDF');
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${link.record_number}_${link.form_type}_${activeCycle.year}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast?.success?.('PDF generated successfully');
    } catch (error) {
      toast?.error?.('Failed to generate PDF');
    }
  }

  function copyLink(url) {
    navigator.clipboard.writeText(url);
    toast?.success?.('Link copied to clipboard');
  }

  function handleExpandLink(linkId) {
    if (expandedLink === linkId) {
      setExpandedLink(null);
    } else {
      setExpandedLink(linkId);
      loadResponses(linkId);
    }
  }

  function handleFormCreated() {
    loadFormLinks();
  }

  // Filter links
  const filteredLinks = formLinks.filter(link => {
    if (filter === 'active' && !link.is_active) return false;
    if (filter === 'inactive' && link.is_active) return false;
    if (typeFilter !== 'all' && link.form_type !== typeFilter) return false;
    return true;
  });

  // Group by record for better organization
  const groupedLinks = filteredLinks.reduce((acc, link) => {
    const key = link.record_number;
    if (!acc[key]) {
      acc[key] = { record_number: link.record_number, record_name: link.record_name, links: [] };
    }
    acc[key].links.push(link);
    return acc;
  }, {});

  const formTypeLabel = (type) => {
    switch (type) {
      case 'staff_declaration': return 'Staff Declaration';
      case 'team_roster': return 'Team Roster';
      case 'simple_signoff': return 'Simple Sign-off';
      case 'table_signoff': return 'Table Sign-off';
      case 'checklist': return 'Checklist';
      default: return type;
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  if (loading) {
    return (
      <div className="forms-view">
        <div className="loading-state">Loading form links...</div>
      </div>
    );
  }

  return (
    <div className="forms-view">
      {/* Template Gallery - Create New Forms */}
      <div className="template-gallery">
        <h3>Create New Form</h3>
        <div className="template-cards">
          <div
            className="template-card"
            onClick={() => setShowStaffDeclaration(true)}
          >
            <span className="template-icon">📋</span>
            <div className="template-info">
              <strong>Staff Declaration</strong>
              <p>Collect acknowledgment signatures from all staff (Record 11)</p>
            </div>
          </div>

          <div
            className="template-card"
            onClick={() => setShowTeamRoster(true)}
          >
            <span className="template-icon">👥</span>
            <div className="template-info">
              <strong>Team Roster</strong>
              <p>Food Safety Team sign-off with configured members (Record 35)</p>
            </div>
          </div>

          <div
            className="template-card"
            onClick={() => setShowSimpleSignoff(true)}
          >
            <span className="template-icon">📄</span>
            <div className="template-info">
              <strong>Simple Sign-off</strong>
              <p>Upload any PDF document for staff to read and sign</p>
            </div>
          </div>

          <div
            className="template-card"
            onClick={() => setShowTableSignoff(true)}
          >
            <span className="template-icon">📊</span>
            <div className="template-info">
              <strong>Table Sign-off</strong>
              <p>Custom table with configurable columns and rows</p>
            </div>
          </div>

          <div className="template-card disabled">
            <span className="template-icon">✅</span>
            <div className="template-info">
              <strong>Checklist</strong>
              <p>Coming soon - dynamic checklist forms</p>
            </div>
          </div>
        </div>
      </div>

      {/* Existing Form Links */}
      {formLinks.length > 0 ? (
        <>
          {/* Header with filters */}
          <div className="forms-header">
            <div className="forms-stats">
              <span className="stat-item">
                <strong>{formLinks.length}</strong> form links
              </span>
              <span className="stat-item">
                <strong>{formLinks.filter(l => l.is_active).length}</strong> active
              </span>
              <span className="stat-item">
                <strong>{formLinks.reduce((sum, l) => sum + (l.response_count || 0), 0)}</strong> total responses
              </span>
            </div>

            <div className="forms-filters">
              <select value={filter} onChange={e => setFilter(e.target.value)}>
                <option value="all">All Links</option>
                <option value="active">Active Only</option>
                <option value="inactive">Inactive Only</option>
              </select>

              <select value={typeFilter} onChange={e => setTypeFilter(e.target.value)}>
                <option value="all">All Types</option>
                <option value="staff_declaration">Staff Declaration</option>
                <option value="team_roster">Team Roster</option>
                <option value="simple_signoff">Simple Sign-off</option>
                <option value="table_signoff">Table Sign-off</option>
              </select>
            </div>
          </div>

          {/* Form Links by Record */}
          <div className="forms-list">
            {Object.values(groupedLinks).map(group => (
              <div key={group.record_number} className="forms-record-group">
                <div className="record-group-header">
                  <span className="record-number">{group.record_number}</span>
                  <span className="record-name">{group.record_name}</span>
                  <span className="link-count">{group.links.length} link{group.links.length !== 1 ? 's' : ''}</span>
                </div>

                {group.links.map(link => (
                  <div key={link.id} className={`form-link-card ${!link.is_active ? 'inactive' : ''}`}>
                    <div className="form-link-header" onClick={() => handleExpandLink(link.id)}>
                      <div className="form-link-info">
                        <span className={`form-type-badge ${link.form_type}`}>
                          {formTypeLabel(link.form_type)}
                        </span>
                        <span className="form-link-title">{link.title}</span>
                        {!link.is_active && <span className="inactive-badge">Inactive</span>}
                      </div>

                      <div className="form-link-progress">
                        <div className="progress-text">
                          <strong>{link.response_count || 0}</strong>
                          {link.expected_responses && (
                            <span> / {link.expected_responses}</span>
                          )}
                          <span className="responses-label"> responses</span>
                        </div>
                        {link.expected_responses && (
                          <div className="progress-bar">
                            <div
                              className="progress-fill"
                              style={{
                                width: `${Math.min(100, ((link.response_count || 0) / link.expected_responses) * 100)}%`,
                                backgroundColor: (link.response_count || 0) >= link.expected_responses
                                  ? 'var(--color-green)'
                                  : 'var(--color-blue)'
                              }}
                            />
                          </div>
                        )}
                      </div>

                      <div className="form-link-actions" onClick={e => e.stopPropagation()}>
                        <button className="btn-icon" title="Copy link" onClick={() => copyLink(link.url)}>📋</button>
                        <button className="btn-icon" title="Download QR code" onClick={() => downloadQR(link)}>📱</button>
                        <button className="btn-icon" title="Download flyer" onClick={() => downloadFlyer(link)}>🖨️</button>
                        <button className="btn-icon" title="Generate PDF" onClick={() => downloadPDF(link)}>📄</button>
                        <button
                          className={`btn-icon ${link.is_active ? 'danger' : 'success'}`}
                          title={link.is_active ? 'Deactivate' : 'Reactivate'}
                          onClick={() => toggleLinkActive(link)}
                        >
                          {link.is_active ? '⏸️' : '▶️'}
                        </button>
                      </div>

                      <span className="expand-icon">{expandedLink === link.id ? '▼' : '▶'}</span>
                    </div>

                    {/* Expanded details */}
                    {expandedLink === link.id && (
                      <div className="form-link-expanded">
                        <div className="link-details">
                          <div className="detail-row">
                            <span className="detail-label">URL:</span>
                            <code className="detail-value url">{link.url}</code>
                          </div>
                          <div className="detail-row">
                            <span className="detail-label">Created:</span>
                            <span className="detail-value">{formatDate(link.created_at)}</span>
                          </div>
                          {link.expires_at && (
                            <div className="detail-row">
                              <span className="detail-label">Expires:</span>
                              <span className="detail-value">{formatDate(link.expires_at)}</span>
                            </div>
                          )}
                        </div>

                        {/* Responses list */}
                        <div className="responses-section">
                          <h4>
                            Responses ({responses[link.id]?.length || link.response_count || 0})
                            {loadingResponses === link.id && <span className="loading-indicator">...</span>}
                          </h4>

                          {responses[link.id]?.length > 0 ? (
                            <div className="responses-table-wrapper">
                              <table className="responses-table">
                                <thead>
                                  <tr>
                                    <th>Name</th>
                                    <th>Role</th>
                                    <th>Department</th>
                                    <th>Signed</th>
                                    <th>Signature</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {responses[link.id].map(resp => (
                                    <tr key={resp.id}>
                                      <td>{resp.respondent_name}</td>
                                      <td>{resp.respondent_role || '-'}</td>
                                      <td>{resp.respondent_dept || '-'}</td>
                                      <td>{formatDate(resp.submitted_at)}</td>
                                      <td>
                                        {resp.signature_data && (
                                          <img
                                            src={resp.signature_data.startsWith('data:')
                                              ? resp.signature_data
                                              : `data:image/png;base64,${resp.signature_data}`}
                                            alt="Signature"
                                            className="signature-preview"
                                          />
                                        )}
                                      </td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          ) : (
                            <p className="no-responses">No responses yet.</p>
                          )}
                        </div>

                        {/* Edit Section */}
                        <div className="edit-section">
                          {editingLink === link.id ? (
                            <div className="edit-form">
                              <div className="edit-field">
                                <label>Title</label>
                                <input
                                  type="text"
                                  value={editForm.title}
                                  onChange={e => setEditForm({ ...editForm, title: e.target.value })}
                                  placeholder="Form title"
                                />
                              </div>
                              <div className="edit-field">
                                <label>Expected Responses</label>
                                <input
                                  type="number"
                                  value={editForm.expected_responses}
                                  onChange={e => setEditForm({ ...editForm, expected_responses: e.target.value })}
                                  placeholder="Leave empty for unlimited"
                                  min="1"
                                />
                              </div>
                              <div className="edit-actions">
                                <button
                                  className="btn-ghost"
                                  onClick={cancelEditing}
                                  disabled={saving}
                                >
                                  Cancel
                                </button>
                                <button
                                  className="btn-primary"
                                  onClick={() => saveEdit(link.id)}
                                  disabled={saving}
                                >
                                  {saving ? 'Saving...' : 'Save Changes'}
                                </button>
                              </div>
                            </div>
                          ) : (
                            <button
                              className="btn-link"
                              onClick={() => startEditing(link)}
                            >
                              Edit form settings
                            </button>
                          )}
                        </div>

                        {/* Delete Section */}
                        <div className="danger-zone">
                          {confirmDelete === link.id ? (
                            <div className="delete-confirm">
                              <p>
                                Delete this form link and all {link.response_count || 0} responses?
                                This cannot be undone.
                              </p>
                              <div className="delete-actions">
                                <button
                                  className="btn-ghost"
                                  onClick={() => setConfirmDelete(null)}
                                  disabled={deletingLink === link.id}
                                >
                                  Cancel
                                </button>
                                <button
                                  className="btn-danger"
                                  onClick={() => deleteFormLink(link)}
                                  disabled={deletingLink === link.id}
                                >
                                  {deletingLink === link.id ? 'Deleting...' : 'Delete Permanently'}
                                </button>
                              </div>
                            </div>
                          ) : (
                            <button
                              className="btn-link danger"
                              onClick={() => setConfirmDelete(link.id)}
                            >
                              Delete this form link
                            </button>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ))}
          </div>
        </>
      ) : (
        <div className="forms-empty-hint">
          <p>No form links created yet. Choose a template above to get started.</p>
        </div>
      )}

      {/* Creation Modals */}
      <SimpleSignoffModal
        isOpen={showSimpleSignoff}
        onClose={() => setShowSimpleSignoff(false)}
        activeCycle={activeCycle}
        records={records}
        onFormCreated={handleFormCreated}
        toast={toast}
      />

      <StaffDeclarationModal
        isOpen={showStaffDeclaration}
        onClose={() => setShowStaffDeclaration(false)}
        activeCycle={activeCycle}
        onFormCreated={handleFormCreated}
        toast={toast}
      />

      <TeamRosterModal
        isOpen={showTeamRoster}
        onClose={() => setShowTeamRoster(false)}
        activeCycle={activeCycle}
        onFormCreated={handleFormCreated}
        toast={toast}
      />

      <TableSignoffModal
        isOpen={showTableSignoff}
        onClose={() => setShowTableSignoff(false)}
        activeCycle={activeCycle}
        records={records}
        onFormCreated={handleFormCreated}
        toast={toast}
      />
    </div>
  );
}
