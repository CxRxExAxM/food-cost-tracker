import { useState, useEffect } from 'react';
import { X, Copy, Download, QrCode, Link, Check, ExternalLink, Users, FileText, Printer, Plus, Trash2 } from 'lucide-react';
import './FormLinkModal.css';

const API_BASE = '/api/ehc';

function getAuthHeaders() {
  const token = localStorage.getItem('token');
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
}

/**
 * Modal for generating and sharing EHC form links
 */
export default function FormLinkModal({
  isOpen,
  onClose,
  submission,
  onLinkCreated,
  onViewResponses
}) {
  const [loading, setLoading] = useState(false);
  const [existingLinks, setExistingLinks] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [copied, setCopied] = useState(false);

  // Create form state
  const [formType, setFormType] = useState('staff_declaration');
  const [expectedResponses, setExpectedResponses] = useState(50);
  const [createdLink, setCreatedLink] = useState(null);

  // Team roster specific state
  const [teamMembers, setTeamMembers] = useState([
    { name: '', position: '', department: '', date_approved: '' }
  ]);

  // Show responses toggle (useful for equipment registration, not for employee privacy)
  const [showResponses, setShowResponses] = useState(false);

  // Table form state (columns + rows)
  const [tableColumns, setTableColumns] = useState([
    { key: 'location', label: 'Location', editable: false, required: false },
    { key: 'name', label: 'Name', editable: true, required: true }
  ]);
  const [tableRows, setTableRows] = useState([
    { location: '' }
  ]);

  // Load existing links when modal opens
  useEffect(() => {
    if (isOpen && submission?.id) {
      loadExistingLinks();
    }
  }, [isOpen, submission?.id]);

  async function loadExistingLinks() {
    try {
      setLoading(true);
      const response = await fetch(
        `${API_BASE}/submissions/${submission.id}/form-links`,
        { headers: getAuthHeaders() }
      );
      if (response.ok) {
        const data = await response.json();
        setExistingLinks(data.data || []);
        // If no links exist, show create form by default
        setShowCreateForm(data.data?.length === 0);
      }
    } catch (err) {
      console.error('Failed to load form links:', err);
    } finally {
      setLoading(false);
    }
  }

  async function createFormLink() {
    // Validate team members for team_roster
    if (formType === 'team_roster') {
      const validMembers = teamMembers.filter(m => m.name.trim());
      if (validMembers.length === 0) {
        alert('Please add at least one team member');
        return;
      }
    }

    // Validate table_form
    if (formType === 'table_form') {
      const validColumns = tableColumns.filter(c => c.label.trim());
      if (validColumns.length === 0) {
        alert('Please add at least one column with a name');
        return;
      }
      const prefillCols = tableColumns.filter(c => !c.editable);
      if (prefillCols.length > 0) {
        const validRows = tableRows.filter(r =>
          prefillCols.some(col => r[col.key]?.trim())
        );
        if (validRows.length === 0) {
          alert('Please add at least one pre-filled row');
          return;
        }
      }
    }

    try {
      setLoading(true);

      // Build config based on form type
      const config = {
        property_name: 'Fairmont Scottsdale Princess',
        show_responses: showResponses
      };

      if (formType === 'team_roster') {
        // Filter out empty rows and include team members
        config.team_members = teamMembers
          .filter(m => m.name.trim())
          .map(m => ({
            name: m.name.trim(),
            position: m.position.trim(),
            department: m.department.trim(),
            date_approved: m.date_approved || new Date().toISOString().split('T')[0]
          }));
      }

      if (formType === 'table_form') {
        // Build columns config (always include signature column)
        config.columns = [
          ...tableColumns.filter(c => c.label.trim()).map(c => ({
            key: c.key,
            label: c.label.trim(),
            editable: c.editable,
            required: c.required
          })),
          { key: 'signature', label: 'Signature', type: 'signature' }
        ];

        // Build rows config (only pre-fill columns)
        const prefillCols = tableColumns.filter(c => !c.editable && c.label.trim());
        config.rows = tableRows
          .filter(r => prefillCols.some(col => r[col.key]?.trim()))
          .map(r => {
            const row = {};
            prefillCols.forEach(col => {
              row[col.key] = r[col.key]?.trim() || '';
            });
            return row;
          });
      }

      // Calculate expected responses
      let expResp = expectedResponses;
      if (formType === 'team_roster') {
        expResp = teamMembers.filter(m => m.name.trim()).length;
      } else if (formType === 'table_form') {
        expResp = config.rows?.length || expectedResponses;
      }

      const response = await fetch(
        `${API_BASE}/submissions/${submission.id}/generate-form-link`,
        {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify({
            form_type: formType,
            expected_responses: expResp,
            config
          })
        }
      );

      if (!response.ok) {
        const text = await response.text();
        let errorMsg = 'Failed to create link';
        try {
          const error = JSON.parse(text);
          errorMsg = error.detail || errorMsg;
        } catch {
          console.error('Server response:', text);
          errorMsg = `Server error (${response.status}): ${text.substring(0, 100)}`;
        }
        throw new Error(errorMsg);
      }

      const data = await response.json();
      setCreatedLink(data);
      setShowCreateForm(false);
      loadExistingLinks();

      if (onLinkCreated) {
        onLinkCreated(data);
      }
    } catch (err) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function copyToClipboard(url) {
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }

  async function downloadQR(linkId) {
    try {
      const response = await fetch(
        `${API_BASE}/form-links/${linkId}/qr`,
        { headers: getAuthHeaders() }
      );
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `qr_form_${linkId}.png`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download QR:', err);
    }
  }

  async function toggleLinkActive(linkId, isActive) {
    try {
      await fetch(`${API_BASE}/form-links/${linkId}`, {
        method: 'PATCH',
        headers: getAuthHeaders(),
        body: JSON.stringify({ is_active: !isActive })
      });
      loadExistingLinks();
    } catch (err) {
      console.error('Failed to update link:', err);
    }
  }

  async function downloadPDF(linkId, formType) {
    try {
      const response = await fetch(
        `${API_BASE}/form-links/${linkId}/generate-pdf`,
        {
          method: 'POST',
          headers: getAuthHeaders()
        }
      );
      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to generate PDF');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const filename = formType === 'staff_declaration'
        ? `Record_11_Staff_Declaration.pdf`
        : `Record_35_Food_Safety_Team.pdf`;
      a.download = filename;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download PDF:', err);
      alert(err.message);
    }
  }

  async function downloadFlyer(linkId) {
    try {
      const response = await fetch(
        `${API_BASE}/form-links/${linkId}/flyer`,
        { headers: getAuthHeaders() }
      );
      if (!response.ok) {
        throw new Error('Failed to generate flyer');
      }
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `QR_Flyer_${linkId}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error('Failed to download flyer:', err);
      alert(err.message);
    }
  }

  // Team member management functions
  function addTeamMember() {
    setTeamMembers([...teamMembers, { name: '', position: '', department: '', date_approved: '' }]);
  }

  function removeTeamMember(index) {
    if (teamMembers.length > 1) {
      setTeamMembers(teamMembers.filter((_, i) => i !== index));
    }
  }

  function updateTeamMember(index, field, value) {
    const updated = [...teamMembers];
    updated[index] = { ...updated[index], [field]: value };
    setTeamMembers(updated);
  }

  // Table form column management
  function addTableColumn() {
    const newKey = `col_${Date.now()}`;
    setTableColumns([...tableColumns, { key: newKey, label: '', editable: true, required: false }]);
  }

  function removeTableColumn(index) {
    if (tableColumns.length > 1) {
      const removed = tableColumns[index];
      setTableColumns(tableColumns.filter((_, i) => i !== index));
      // Also remove this column's data from all rows
      setTableRows(tableRows.map(row => {
        const { [removed.key]: _, ...rest } = row;
        return rest;
      }));
    }
  }

  function updateTableColumn(index, field, value) {
    const updated = [...tableColumns];
    if (field === 'label') {
      // Auto-generate key from label if it's a new column
      const col = updated[index];
      if (col.key.startsWith('col_')) {
        const newKey = value.toLowerCase().replace(/\s+/g, '_').replace(/[^a-z0-9_]/g, '');
        if (newKey) {
          // Update row data keys
          setTableRows(tableRows.map(row => {
            const { [col.key]: val, ...rest } = row;
            return { ...rest, [newKey]: val || '' };
          }));
          col.key = newKey;
        }
      }
    }
    updated[index] = { ...updated[index], [field]: value };
    setTableColumns(updated);
  }

  // Table form row management
  function addTableRow() {
    const newRow = {};
    tableColumns.filter(c => !c.editable).forEach(c => {
      newRow[c.key] = '';
    });
    setTableRows([...tableRows, newRow]);
  }

  function removeTableRow(index) {
    if (tableRows.length > 1) {
      setTableRows(tableRows.filter((_, i) => i !== index));
    }
  }

  function updateTableRow(index, key, value) {
    const updated = [...tableRows];
    updated[index] = { ...updated[index], [key]: value };
    setTableRows(updated);
  }

  if (!isOpen) return null;

  const formTypeOptions = [
    { value: 'staff_declaration', label: 'Staff Declaration', desc: 'Self-fill form — users enter all their info' },
    { value: 'team_roster', label: 'Team Roster', desc: 'Pre-filled names — each person finds and signs' },
    { value: 'table_form', label: 'Table Form (Custom)', desc: 'Define columns & rows — partial pre-fill supported' }
  ];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="form-link-modal" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Form Link</h2>
          <span className="modal-subtitle">
            {submission?.record_name} — {submission?.period_label}
          </span>
          <button className="modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <div className="modal-content">
          {loading && !createdLink && (
            <div className="loading-state">Loading...</div>
          )}

          {/* Just Created Link - Show prominently */}
          {createdLink && (
            <div className="created-link-section">
              <div className={`success-banner ${createdLink.reused ? 'reused' : ''}`}>
                <Check size={20} />
                <span>{createdLink.reused ? 'Using existing link' : 'Form link created!'}</span>
              </div>

              <div className="qr-display">
                <img
                  src={`data:image/png;base64,${createdLink.qr_code}`}
                  alt="QR Code"
                  className="qr-image"
                />
              </div>

              <div className="link-url-box">
                <input
                  type="text"
                  readOnly
                  value={createdLink.url}
                  className="link-url-input"
                />
                <button
                  className="btn-copy"
                  onClick={() => copyToClipboard(createdLink.url)}
                >
                  {copied ? <Check size={16} /> : <Copy size={16} />}
                  {copied ? 'Copied!' : 'Copy'}
                </button>
              </div>

              <div className="link-actions">
                <button
                  className="btn-secondary"
                  onClick={() => downloadQR(createdLink.form_link_id)}
                >
                  <Download size={16} />
                  Download QR
                </button>
                <a
                  href={createdLink.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="btn-secondary"
                >
                  <ExternalLink size={16} />
                  Open Form
                </a>
              </div>

              <div className="pdf-actions">
                <button
                  className="btn-secondary"
                  onClick={() => downloadFlyer(createdLink.form_link_id)}
                  title="Download printable flyer with QR code"
                >
                  <Printer size={16} />
                  Print Flyer
                </button>
                <button
                  className="btn-secondary"
                  onClick={() => downloadPDF(createdLink.form_link_id, createdLink.form_type)}
                  title="Download PDF with collected signatures"
                >
                  <FileText size={16} />
                  Export PDF
                </button>
              </div>

              <button
                className="btn-ghost"
                onClick={() => setCreatedLink(null)}
              >
                Done
              </button>
            </div>
          )}

          {/* Existing Links */}
          {!createdLink && existingLinks.length > 0 && (
            <div className="existing-links-section">
              <h3>Active Links</h3>
              {existingLinks.map(link => (
                <div key={link.id} className={`link-card ${!link.is_active ? 'inactive' : ''}`}>
                  <div className="link-card-header">
                    <span className="link-type-badge">
                      {link.form_type === 'staff_declaration' && 'Declaration'}
                      {link.form_type === 'team_roster' && 'Team Roster'}
                      {link.form_type === 'table_form' && 'Table Form'}
                    </span>
                    <button
                      className="link-responses-btn"
                      onClick={() => onViewResponses && onViewResponses(link)}
                      title="View responses"
                    >
                      <Users size={12} />
                      {link.response_count}{link.expected_responses ? `/${link.expected_responses}` : ''} responses
                    </button>
                    {!link.is_active && (
                      <span className="link-inactive-badge">Inactive</span>
                    )}
                  </div>

                  <div className="link-url-row">
                    <input
                      type="text"
                      readOnly
                      value={link.url}
                      className="link-url-input small"
                    />
                    <button
                      className="btn-icon"
                      onClick={() => copyToClipboard(link.url)}
                      title="Copy link"
                    >
                      <Copy size={14} />
                    </button>
                    <button
                      className="btn-icon"
                      onClick={() => downloadQR(link.id)}
                      title="Download QR"
                    >
                      <QrCode size={14} />
                    </button>
                    <a
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn-icon"
                      title="Open form"
                    >
                      <ExternalLink size={14} />
                    </a>
                  </div>

                  <div className="link-card-actions">
                    <button
                      className="btn-icon"
                      onClick={() => downloadFlyer(link.id)}
                      title="Download printable flyer"
                    >
                      <Printer size={14} />
                    </button>
                    <button
                      className="btn-icon"
                      onClick={() => downloadPDF(link.id, link.form_type)}
                      title="Export signatures PDF"
                    >
                      <FileText size={14} />
                    </button>
                    <button
                      className="btn-ghost btn-sm"
                      onClick={() => toggleLinkActive(link.id, link.is_active)}
                    >
                      {link.is_active ? 'Deactivate' : 'Reactivate'}
                    </button>
                  </div>
                </div>
              ))}

              <button
                className="btn-secondary btn-new-link"
                onClick={() => setShowCreateForm(true)}
              >
                <Link size={16} />
                Create Another Link
              </button>
            </div>
          )}

          {/* Create Form */}
          {!createdLink && (showCreateForm || existingLinks.length === 0) && !loading && (
            <div className="create-form-section">
              <h3>{existingLinks.length > 0 ? 'Create New Link' : 'Generate Form Link'}</h3>

              <div className="form-field">
                <label>Form Type</label>
                <div className="form-type-options">
                  {formTypeOptions.map(opt => (
                    <label
                      key={opt.value}
                      className={`form-type-option ${formType === opt.value ? 'selected' : ''}`}
                    >
                      <input
                        type="radio"
                        name="formType"
                        value={opt.value}
                        checked={formType === opt.value}
                        onChange={e => setFormType(e.target.value)}
                      />
                      <div className="option-content">
                        <span className="option-label">{opt.label}</span>
                        <span className="option-desc">{opt.desc}</span>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Show Responses Toggle - visible for all form types */}
              <div className="form-field">
                <label className="toggle-label">
                  <input
                    type="checkbox"
                    checked={showResponses}
                    onChange={e => setShowResponses(e.target.checked)}
                    className="toggle-checkbox"
                  />
                  <span className="toggle-text">Show existing responses on public form</span>
                </label>
                <span className="field-hint">
                  Useful for equipment registration. Disable for employee privacy.
                </span>
              </div>

              {/* Expected Responses - only for staff_declaration */}
              {formType === 'staff_declaration' && (
                <div className="form-field">
                  <label htmlFor="expectedResponses">Expected Responses</label>
                  <input
                    id="expectedResponses"
                    type="number"
                    min="1"
                    max="500"
                    value={expectedResponses}
                    onChange={e => setExpectedResponses(parseInt(e.target.value) || 50)}
                    className="input"
                  />
                  <span className="field-hint">
                    Used for progress tracking (e.g., 95 staff members)
                  </span>
                </div>
              )}

              {/* Team Members Editor - only for team_roster */}
              {formType === 'team_roster' && (
                <div className="form-field">
                  <label>Food Safety Team Members</label>
                  <span className="field-hint" style={{ marginBottom: 'var(--space-2)' }}>
                    Add team members who will sign. Each person finds their name and signs.
                  </span>

                  <div className="team-members-editor">
                    {teamMembers.map((member, idx) => (
                      <div key={idx} className="team-member-row">
                        <input
                          type="text"
                          placeholder="Name *"
                          value={member.name}
                          onChange={e => updateTeamMember(idx, 'name', e.target.value)}
                          className="input team-input name"
                        />
                        <input
                          type="text"
                          placeholder="Position"
                          value={member.position}
                          onChange={e => updateTeamMember(idx, 'position', e.target.value)}
                          className="input team-input"
                        />
                        <input
                          type="text"
                          placeholder="Department"
                          value={member.department}
                          onChange={e => updateTeamMember(idx, 'department', e.target.value)}
                          className="input team-input"
                        />
                        <button
                          type="button"
                          className="btn-icon btn-remove"
                          onClick={() => removeTeamMember(idx)}
                          disabled={teamMembers.length === 1}
                          title="Remove member"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    ))}

                    <button
                      type="button"
                      className="btn-add-member"
                      onClick={addTeamMember}
                    >
                      <Plus size={14} />
                      Add Team Member
                    </button>
                  </div>

                  <span className="field-hint" style={{ marginTop: 'var(--space-2)' }}>
                    {teamMembers.filter(m => m.name.trim()).length} team member(s) configured
                  </span>
                </div>
              )}

              {/* Table Form Editor */}
              {formType === 'table_form' && (
                <div className="form-field">
                  <label>Define Columns</label>
                  <span className="field-hint" style={{ marginBottom: 'var(--space-2)' }}>
                    Non-editable columns = you pre-fill. Editable = user fills when signing.
                  </span>

                  <div className="table-columns-editor">
                    {tableColumns.map((col, idx) => (
                      <div key={idx} className="table-column-row">
                        <input
                          type="text"
                          placeholder="Column name"
                          value={col.label}
                          onChange={e => updateTableColumn(idx, 'label', e.target.value)}
                          className="input table-col-input"
                        />
                        <label className="col-toggle">
                          <input
                            type="checkbox"
                            checked={!col.editable}
                            onChange={e => updateTableColumn(idx, 'editable', !e.target.checked)}
                          />
                          <span>Pre-fill</span>
                        </label>
                        <label className="col-toggle">
                          <input
                            type="checkbox"
                            checked={col.required}
                            onChange={e => updateTableColumn(idx, 'required', e.target.checked)}
                          />
                          <span>Required</span>
                        </label>
                        <button
                          type="button"
                          className="btn-icon btn-remove"
                          onClick={() => removeTableColumn(idx)}
                          disabled={tableColumns.length === 1}
                          title="Remove column"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    ))}
                    <button
                      type="button"
                      className="btn-add-member"
                      onClick={addTableColumn}
                    >
                      <Plus size={14} />
                      Add Column
                    </button>
                  </div>

                  {/* Pre-filled rows (only for non-editable columns) */}
                  {tableColumns.some(c => !c.editable) && (
                    <>
                      <label style={{ marginTop: 'var(--space-4)' }}>Pre-fill Rows</label>
                      <span className="field-hint" style={{ marginBottom: 'var(--space-2)' }}>
                        Add one row per item (e.g., each location). Users will find their row and complete it.
                      </span>

                      <div className="table-rows-editor">
                        {tableRows.map((row, rowIdx) => (
                          <div key={rowIdx} className="table-row-entry">
                            {tableColumns.filter(c => !c.editable).map(col => (
                              <input
                                key={col.key}
                                type="text"
                                placeholder={col.label || col.key}
                                value={row[col.key] || ''}
                                onChange={e => updateTableRow(rowIdx, col.key, e.target.value)}
                                className="input table-row-input"
                              />
                            ))}
                            <button
                              type="button"
                              className="btn-icon btn-remove"
                              onClick={() => removeTableRow(rowIdx)}
                              disabled={tableRows.length === 1}
                              title="Remove row"
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        ))}
                        <button
                          type="button"
                          className="btn-add-member"
                          onClick={addTableRow}
                        >
                          <Plus size={14} />
                          Add Row
                        </button>
                      </div>

                      <span className="field-hint" style={{ marginTop: 'var(--space-2)' }}>
                        {tableRows.filter(r => Object.values(r).some(v => v?.trim())).length} row(s) configured
                      </span>
                    </>
                  )}
                </div>
              )}

              <div className="form-actions">
                {existingLinks.length > 0 && (
                  <button
                    className="btn-ghost"
                    onClick={() => setShowCreateForm(false)}
                  >
                    Cancel
                  </button>
                )}
                <button
                  className="btn-primary"
                  onClick={createFormLink}
                  disabled={loading}
                >
                  {loading ? 'Creating...' : 'Generate Link'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
