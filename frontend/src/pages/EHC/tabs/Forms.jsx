/**
 * Forms Tab Component
 *
 * Admin workbench for digital form management:
 * - Create new sign-off forms
 * - View all form links for the current cycle
 * - Track response progress
 * - Quick actions: QR, Flyer, Responses, Edit, Delete
 */

import { useState, useEffect } from 'react';
import {
  API_BASE,
  fetchWithAuth,
} from './shared';
import TableSignoffModal from '../modals/TableSignoffModal';
import CreateFromTemplateModal from '../modals/CreateFromTemplateModal';

export default function Forms({ activeCycle, toast }) {
  const [formLinks, setFormLinks] = useState([]);
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [expandedLink, setExpandedLink] = useState(null);
  const [responses, setResponses] = useState({});
  const [loadingResponses, setLoadingResponses] = useState(null);
  const [deletingLink, setDeletingLink] = useState(null);
  const [confirmDelete, setConfirmDelete] = useState(null);

  // Modal state
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [showCreateFromTemplate, setShowCreateFromTemplate] = useState(false);
  const [editingFormLink, setEditingFormLink] = useState(null); // Full link object for edit mode
  const [duplicatingFormLink, setDuplicatingFormLink] = useState(null); // Form link to duplicate

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
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Failed to generate PDF');
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      // Use outlet_name for checklist forms, record_number for others
      const identifier = link.outlet_name || link.record_number || 'form';
      a.download = `${identifier}_${link.form_type}_${activeCycle.year}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
      toast?.success?.('PDF generated successfully');
    } catch (error) {
      console.error('PDF generation error:', error);
      toast?.error?.(error.message || 'Failed to generate PDF');
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
    return true;
  });

  // Group by template+period (for template-based) or record (for regular forms)
  const groupedLinks = filteredLinks.reduce((acc, link) => {
    let key, groupName, groupType;

    if (link.template_id && link.template_name) {
      // Template-based: group by template + period
      key = `template_${link.template_id}_${link.period_label || 'no-period'}`;
      groupName = `${link.template_name} - ${link.period_label || ''}`;
      groupType = 'template';
    } else {
      // Regular: group by record
      key = `record_${link.record_number}`;
      groupName = `${link.record_number} - ${link.record_name}`;
      groupType = 'record';
    }

    if (!acc[key]) {
      acc[key] = {
        key,
        group_name: groupName,
        group_type: groupType,
        record_number: link.record_number,
        record_name: link.record_name,
        template_name: link.template_name,
        period_label: link.period_label,
        links: []
      };
    }
    acc[key].links.push(link);
    return acc;
  }, {});

  const formTypeLabel = (type) => {
    switch (type) {
      case 'checklist_form':
        return 'Checklist';
      case 'table_signoff':
        return 'Sign-off Form';
      case 'staff_declaration':
        return 'Staff Declaration';
      case 'team_roster':
        return 'Team Roster';
      default:
        return 'Form';
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  };

  // Render responses table dynamically based on form type
  const renderResponsesTable = (link, respList) => {
    // For table_signoff, use dynamic columns from config
    if (link.form_type === 'table_signoff' && link.config?.columns) {
      const columns = link.config.columns.filter(c => c.type !== 'signature');
      return (
        <table className="responses-table">
          <thead>
            <tr>
              {columns.map(col => (
                <th key={col.key}>{col.label || col.key}</th>
              ))}
              <th>Signed</th>
              <th>Signature</th>
            </tr>
          </thead>
          <tbody>
            {respList.map(resp => (
              <tr key={resp.id}>
                {columns.map(col => (
                  <td key={col.key}>
                    {resp.response_data?.row_data?.[col.key] || resp.respondent_name || '-'}
                  </td>
                ))}
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
      );
    }

    // For team_roster, show name, position, department
    if (link.form_type === 'team_roster') {
      return (
        <table className="responses-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Position</th>
              <th>Department</th>
              <th>Signed</th>
              <th>Signature</th>
            </tr>
          </thead>
          <tbody>
            {respList.map(resp => (
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
      );
    }

    // Default: staff_declaration and others - just name and signature
    return (
      <table className="responses-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Signed</th>
            <th>Signature</th>
          </tr>
        </thead>
        <tbody>
          {respList.map(resp => (
            <tr key={resp.id}>
              <td>{resp.respondent_name}</td>
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
    );
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
      {/* Create Form Header */}
      <div className="forms-header">
        <h3>Sign-off Forms</h3>
        <div className="header-actions">
          <button className="btn-secondary" onClick={() => setShowCreateFromTemplate(true)}>
            From Template
          </button>
          <button className="btn-primary" onClick={() => setShowCreateForm(true)}>
            + Create Form
          </button>
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
            </div>
          </div>

          {/* Form Links by Group */}
          <div className="forms-list">
            {Object.values(groupedLinks).map(group => (
              <div key={group.key} className={`forms-record-group ${group.group_type === 'template' ? 'template-group' : ''}`}>
                <div className="record-group-header">
                  {group.group_type === 'template' ? (
                    <>
                      <span className="template-badge">Template</span>
                      <span className="record-name">{group.template_name}</span>
                      {group.period_label && <span className="period-badge">{group.period_label}</span>}
                    </>
                  ) : (
                    <>
                      <span className="record-number">{group.record_number}</span>
                      <span className="record-name">{group.record_name}</span>
                    </>
                  )}
                  <span className="link-count">{group.links.length} link{group.links.length !== 1 ? 's' : ''}</span>
                </div>

                {group.links.map(link => (
                  <div key={link.id} className={`form-link-card ${!link.is_active ? 'inactive' : ''}`}>
                    <div className="form-link-header" onClick={() => handleExpandLink(link.id)}>
                      <div className="form-link-info">
                        <span className={`form-type-badge ${link.form_type}`}>
                          {formTypeLabel(link.form_type)}
                        </span>
                        {link.outlet_name ? (
                          <span className="form-link-title outlet-name">{link.outlet_name}</span>
                        ) : (
                          <span className="form-link-title">{link.title}</span>
                        )}
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
                              {renderResponsesTable(link, responses[link.id])}
                            </div>
                          ) : (
                            <p className="no-responses">No responses yet.</p>
                          )}
                        </div>

                        {/* Edit & Duplicate Section */}
                        <div className="edit-section">
                          <button
                            className="btn-link"
                            onClick={() => setEditingFormLink(link)}
                          >
                            Edit form (columns, rows, settings)
                          </button>
                          <span className="edit-separator">•</span>
                          <button
                            className="btn-link"
                            onClick={() => setDuplicatingFormLink(link)}
                          >
                            Duplicate as template
                          </button>
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
          <p>No form links created yet. Click "Create Form" to get started.</p>
        </div>
      )}

      {/* Create/Edit/Duplicate Form Modal */}
      <TableSignoffModal
        isOpen={showCreateForm || !!editingFormLink || !!duplicatingFormLink}
        onClose={() => {
          setShowCreateForm(false);
          setEditingFormLink(null);
          setDuplicatingFormLink(null);
        }}
        activeCycle={activeCycle}
        records={records}
        editingLink={editingFormLink}
        duplicateFrom={duplicatingFormLink}
        onFormCreated={() => {
          setShowCreateForm(false);
          setEditingFormLink(null);
          setDuplicatingFormLink(null);
          loadFormLinks();
        }}
        toast={toast}
      />

      {/* Create from Template Modal */}
      <CreateFromTemplateModal
        isOpen={showCreateFromTemplate}
        onClose={() => setShowCreateFromTemplate(false)}
        activeCycle={activeCycle}
        onFormsCreated={() => {
          setShowCreateFromTemplate(false);
          loadFormLinks();
        }}
        toast={toast}
      />
    </div>
  );
}
