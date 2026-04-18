/**
 * Settings Tab Component
 *
 * Module configuration:
 * - Audit cycle management (status, dates)
 * - EHC Outlets (kitchens, restaurants, bars)
 * - EHC Contacts (people assigned to outlets for email distribution)
 * - Email Configuration (Resend integration status)
 * - Responsibility Codes (custom role definitions)
 */

import { useState, useEffect } from 'react';
import {
  API_BASE,
  fetchWithAuth,
  getAuthHeaders,
} from './shared';
import OutletModal from '../modals/OutletModal';
import ContactModal from '../modals/ContactModal';
import { X, Edit2, Plus, Mail, Check, Send, CheckCircle, AlertCircle, Clock, Thermometer, QrCode, Download, RefreshCw } from 'lucide-react';

export default function Settings({ activeCycle, onCycleUpdated, toast }) {
  const [updating, setUpdating] = useState(false);
  const [showStatusConfirm, setShowStatusConfirm] = useState(null);

  // Outlets state
  const [outlets, setOutlets] = useState([]);
  const [loadingOutlets, setLoadingOutlets] = useState(true);
  const [outletModal, setOutletModal] = useState({ show: false, outlet: null });

  // Contacts state
  const [contacts, setContacts] = useState([]);
  const [loadingContacts, setLoadingContacts] = useState(true);
  const [contactModal, setContactModal] = useState({ show: false, contact: null });

  // Responsibility codes state
  const [respCodes, setRespCodes] = useState([]);
  const [loadingCodes, setLoadingCodes] = useState(true);
  const [editingCodeId, setEditingCodeId] = useState(null);
  const [codeEditData, setCodeEditData] = useState({});

  // Email state
  const [emailStatus, setEmailStatus] = useState(null);
  const [loadingEmailStatus, setLoadingEmailStatus] = useState(true);
  const [emailLog, setEmailLog] = useState([]);
  const [loadingEmailLog, setLoadingEmailLog] = useState(true);
  const [sendingTestEmail, setSendingTestEmail] = useState(false);

  // Daily Log QR state
  const [qrModal, setQrModal] = useState({ show: false, outlet: null });
  const [qrData, setQrData] = useState(null);
  const [loadingQr, setLoadingQr] = useState(false);
  const [generatingToken, setGeneratingToken] = useState(false);

  const cycleStatuses = [
    { value: 'preparing', label: 'Preparing', description: 'Setting up records and collecting evidence' },
    { value: 'in_progress', label: 'In Progress', description: 'Audit is underway' },
    { value: 'completed', label: 'Completed', description: 'Audit finished and reviewed' },
    { value: 'archived', label: 'Archived', description: 'Historical record' },
  ];

  const outletTypes = [
    'Production Kitchen',
    'Restaurant',
    'Bar',
    'Lounge',
    'Support',
    'Franchise',
    'Other'
  ];

  // Load outlets
  useEffect(() => {
    loadOutlets();
  }, []);

  // Load contacts
  useEffect(() => {
    loadContacts();
  }, []);

  // Load responsibility codes
  useEffect(() => {
    loadRespCodes();
  }, []);

  // Load email status and log
  useEffect(() => {
    loadEmailStatus();
    loadEmailLog();
  }, []);

  async function loadOutlets() {
    try {
      setLoadingOutlets(true);
      const data = await fetchWithAuth(`${API_BASE}/outlets?active_only=true`);
      setOutlets(data.data || []);
    } catch (error) {
      toast?.error?.('Failed to load outlets');
    } finally {
      setLoadingOutlets(false);
    }
  }

  async function loadContacts() {
    try {
      setLoadingContacts(true);
      const data = await fetchWithAuth(`${API_BASE}/contacts?active_only=true`);
      setContacts(data.data || []);
    } catch (error) {
      toast?.error?.('Failed to load contacts');
    } finally {
      setLoadingContacts(false);
    }
  }

  async function loadRespCodes() {
    try {
      setLoadingCodes(true);
      const data = await fetchWithAuth(`${API_BASE}/responsibility-codes?active_only=true`);
      setRespCodes(data.data || []);
    } catch (error) {
      toast?.error?.('Failed to load responsibility codes');
    } finally {
      setLoadingCodes(false);
    }
  }

  async function loadEmailStatus() {
    try {
      setLoadingEmailStatus(true);
      const data = await fetchWithAuth(`${API_BASE}/email/status`);
      setEmailStatus(data);
    } catch (error) {
      setEmailStatus({ configured: false, error: 'Failed to check status' });
    } finally {
      setLoadingEmailStatus(false);
    }
  }

  async function loadEmailLog() {
    try {
      setLoadingEmailLog(true);
      const data = await fetchWithAuth(`${API_BASE}/email/log?limit=10`);
      setEmailLog(data.data || []);
    } catch (error) {
      // Email log may not exist yet, that's okay
      setEmailLog([]);
    } finally {
      setLoadingEmailLog(false);
    }
  }

  async function handleSendTestEmail() {
    try {
      setSendingTestEmail(true);
      await fetchWithAuth(`${API_BASE}/email/test`, {
        method: 'POST'
      });
      toast?.success?.('Test email sent! Check your inbox.');
      loadEmailLog(); // Refresh log
    } catch (error) {
      toast?.error?.(error.message || 'Failed to send test email');
    } finally {
      setSendingTestEmail(false);
    }
  }

  // Open QR modal for an outlet
  async function handleShowQr(outlet) {
    setQrModal({ show: true, outlet });
    setQrData(null);

    // Check if outlet already has a token
    if (outlet.daily_log_token) {
      await loadQrCode(outlet.name);
    }
  }

  // Load existing QR code
  async function loadQrCode(outletName) {
    try {
      setLoadingQr(true);
      // Need to use auth headers - this endpoint returns binary PNG, not JSON
      const headers = getAuthHeaders();
      delete headers['Content-Type']; // Don't set content-type for GET request
      const response = await fetch(`/api/daily-log/outlets/${encodeURIComponent(outletName)}/qr-code`, {
        headers
      });
      if (!response.ok) {
        throw new Error('Failed to load QR code');
      }
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      setQrData(url);
    } catch (error) {
      toast?.error?.('Failed to load QR code');
    } finally {
      setLoadingQr(false);
    }
  }

  // Generate new token for outlet
  async function handleGenerateToken() {
    if (!qrModal.outlet) return;

    try {
      setGeneratingToken(true);
      const result = await fetchWithAuth(`/api/daily-log/outlets/${encodeURIComponent(qrModal.outlet.name)}/generate-token`, {
        method: 'POST'
      });
      toast?.success?.('Access link generated');
      // Update modal's outlet state to reflect token exists
      setQrModal(prev => ({
        ...prev,
        outlet: { ...prev.outlet, daily_log_token: result.token }
      }));
      // Reload outlet data and QR code
      await loadOutlets();
      await loadQrCode(qrModal.outlet.name);
    } catch (error) {
      toast?.error?.(error.message || 'Failed to generate access link');
    } finally {
      setGeneratingToken(false);
    }
  }

  // Download QR code image
  function handleDownloadQr() {
    if (!qrData || !qrModal.outlet) return;

    const link = document.createElement('a');
    link.href = qrData;
    link.download = `daily-log-qr-${qrModal.outlet.name}.png`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  // Close QR modal and cleanup
  function closeQrModal() {
    if (qrData) {
      URL.revokeObjectURL(qrData);
    }
    setQrModal({ show: false, outlet: null });
    setQrData(null);
  }

  async function updateCycleStatus(newStatus) {
    try {
      setUpdating(true);
      await fetchWithAuth(`${API_BASE}/cycles/${activeCycle.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus })
      });
      toast?.success?.(`Cycle status updated to ${newStatus.replace('_', ' ')}`);
      onCycleUpdated?.();
      setShowStatusConfirm(null);
    } catch (error) {
      toast?.error?.('Failed to update cycle status');
    } finally {
      setUpdating(false);
    }
  }

  async function handleSaveOutlet(outletData) {
    try {
      if (outletData.id) {
        // Update existing
        await fetchWithAuth(`${API_BASE}/outlets/${outletData.id}`, {
          method: 'PATCH',
          body: JSON.stringify(outletData)
        });
        toast?.success?.('Outlet updated');
      } else {
        // Create new
        await fetchWithAuth(`${API_BASE}/outlets`, {
          method: 'POST',
          body: JSON.stringify(outletData)
        });
        toast?.success?.('Outlet created');
      }
      loadOutlets();
      setOutletModal({ show: false, outlet: null });
    } catch (error) {
      toast?.error?.(error.message || 'Failed to save outlet');
      throw error;
    }
  }

  async function handleDeleteOutlet(outletId) {
    if (!confirm('Deactivate this outlet? It will be hidden from active lists but historical references will remain.')) {
      return;
    }

    try {
      await fetchWithAuth(`${API_BASE}/outlets/${outletId}`, {
        method: 'DELETE'
      });
      toast?.success?.('Outlet deactivated');
      loadOutlets();
      setOutletModal({ show: false, outlet: null });
    } catch (error) {
      toast?.error?.('Failed to deactivate outlet');
    }
  }

  async function handleSaveContact(contactData, outletAssignments) {
    try {
      let savedContact;
      if (contactData.id) {
        // Update existing contact
        savedContact = await fetchWithAuth(`${API_BASE}/contacts/${contactData.id}`, {
          method: 'PATCH',
          body: JSON.stringify(contactData)
        });
      } else {
        // Create new contact
        savedContact = await fetchWithAuth(`${API_BASE}/contacts`, {
          method: 'POST',
          body: JSON.stringify(contactData)
        });
      }

      // Set outlet assignments
      if (savedContact?.id) {
        await fetchWithAuth(`${API_BASE}/contacts/${savedContact.id}/outlets`, {
          method: 'POST',
          body: JSON.stringify({ outlets: outletAssignments })
        });
      }

      toast?.success?.(contactData.id ? 'Contact updated' : 'Contact created');
      loadContacts();
      setContactModal({ show: false, contact: null });
    } catch (error) {
      toast?.error?.(error.message || 'Failed to save contact');
      throw error;
    }
  }

  async function handleDeleteContact(contactId) {
    if (!confirm('Deactivate this contact? They will be hidden from active lists.')) {
      return;
    }

    try {
      await fetchWithAuth(`${API_BASE}/contacts/${contactId}`, {
        method: 'DELETE'
      });
      toast?.success?.('Contact deactivated');
      loadContacts();
      setContactModal({ show: false, contact: null });
    } catch (error) {
      toast?.error?.('Failed to deactivate contact');
    }
  }

  async function handleUpdateRespCode(codeId, updates) {
    try {
      await fetchWithAuth(`${API_BASE}/responsibility-codes/${codeId}`, {
        method: 'PATCH',
        body: JSON.stringify(updates)
      });
      toast?.success?.('Responsibility code updated');
      loadRespCodes();
      setEditingCodeId(null);
      setCodeEditData({});
    } catch (error) {
      toast?.error?.('Failed to update responsibility code');
    }
  }

  async function handleDeleteRespCode(codeId) {
    if (!confirm('Deactivate this responsibility code?')) {
      return;
    }

    try {
      await fetchWithAuth(`${API_BASE}/responsibility-codes/${codeId}`, {
        method: 'DELETE'
      });
      toast?.success?.('Responsibility code deactivated');
      loadRespCodes();
    } catch (error) {
      toast?.error?.('Failed to deactivate responsibility code');
    }
  }

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Not set';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      weekday: 'long',
      month: 'long',
      day: 'numeric',
      year: 'numeric'
    });
  };

  const getDaysUntil = (dateStr) => {
    if (!dateStr) return null;
    const target = new Date(dateStr);
    const now = new Date();
    const days = Math.ceil((target - now) / (1000 * 60 * 60 * 24));
    return days;
  };

  const daysUntil = getDaysUntil(activeCycle?.target_date);

  // Group outlets by type
  const outletsByType = outlets.reduce((acc, outlet) => {
    const type = outlet.outlet_type || 'Other';
    if (!acc[type]) acc[type] = [];
    acc[type].push(outlet);
    return acc;
  }, {});

  // Sort outlet groups
  const typeOrder = ['Production Kitchen', 'Restaurant', 'Bar', 'Lounge', 'Support', 'Franchise', 'Other'];
  const sortedTypes = typeOrder.filter(type => outletsByType[type]);

  // Helper to generate monitoring summary for an outlet
  const getMonitoringSummary = (outlet) => {
    if (!outlet.daily_monitoring_enabled) {
      return null;
    }

    const parts = [];
    if (outlet.cooler_count > 0) {
      parts.push(`${outlet.cooler_count} cooler${outlet.cooler_count > 1 ? 's' : ''}`);
    }
    if (outlet.freezer_count > 0) {
      parts.push(`${outlet.freezer_count} freezer${outlet.freezer_count > 1 ? 's' : ''}`);
    }

    const capabilities = [];
    if (outlet.has_cooking) capabilities.push('Cook');
    if (outlet.has_cooling) capabilities.push('Cool');
    if (outlet.has_thawing) capabilities.push('Thaw');

    if (capabilities.length > 0) {
      parts.push(capabilities.join('/'));
    }

    return parts.length > 0 ? parts.join(', ') : 'Enabled';
  };

  return (
    <div className="settings-view-content">
      {/* Cycle Overview */}
      <section className="settings-section">
        <h2>Audit Cycle Overview</h2>

        <div className="settings-card">
          <div className="cycle-info-grid">
            <div className="info-item">
              <span className="info-label">Cycle</span>
              <span className="info-value large">EHC {activeCycle?.year}</span>
            </div>

            <div className="info-item">
              <span className="info-label">Status</span>
              <span className={`status-badge ${activeCycle?.status}`}>
                {activeCycle?.status?.replace('_', ' ')}
              </span>
            </div>

            <div className="info-item">
              <span className="info-label">Audit Date</span>
              <span className="info-value">
                {formatDate(activeCycle?.target_date)}
                {daysUntil !== null && (
                  <span className={`days-badge ${daysUntil <= 30 ? 'urgent' : ''}`}>
                    {daysUntil > 0
                      ? `${daysUntil} days away`
                      : daysUntil === 0
                        ? 'Today!'
                        : `${Math.abs(daysUntil)} days ago`}
                  </span>
                )}
              </span>
            </div>

            <div className="info-item">
              <span className="info-label">Created</span>
              <span className="info-value">{formatDate(activeCycle?.created_at)}</span>
            </div>
          </div>
        </div>
      </section>

      {/* Status Management */}
      <section className="settings-section">
        <h2>Cycle Status</h2>
        <p className="section-description">
          Update the cycle status to reflect the current phase of the audit.
        </p>

        <div className="status-options">
          {cycleStatuses.map(status => (
            <div
              key={status.value}
              className={`status-option ${activeCycle?.status === status.value ? 'current' : ''}`}
            >
              <div className="status-option-header">
                <span className={`status-indicator ${status.value}`}></span>
                <strong>{status.label}</strong>
                {activeCycle?.status === status.value && (
                  <span className="current-label">Current</span>
                )}
              </div>
              <p className="status-description">{status.description}</p>
              {activeCycle?.status !== status.value && (
                <button
                  className="btn-sm"
                  onClick={() => setShowStatusConfirm(status.value)}
                  disabled={updating}
                >
                  Set as {status.label}
                </button>
              )}
            </div>
          ))}
        </div>

        {/* Status change confirmation */}
        {showStatusConfirm && (
          <div className="confirm-dialog">
            <p>
              Change cycle status to <strong>{showStatusConfirm.replace('_', ' ')}</strong>?
            </p>
            <div className="confirm-actions">
              <button
                className="btn-ghost"
                onClick={() => setShowStatusConfirm(null)}
                disabled={updating}
              >
                Cancel
              </button>
              <button
                className="btn-primary"
                onClick={() => updateCycleStatus(showStatusConfirm)}
                disabled={updating}
              >
                {updating ? 'Updating...' : 'Confirm'}
              </button>
            </div>
          </div>
        )}
      </section>

      {/* EHC Outlets */}
      <section className="settings-section">
        <div className="section-header">
          <div>
            <h2>EHC Outlets</h2>
            <p className="section-description">
              Property areas for record tracking and form distribution. Assign leaders via Contacts below.
            </p>
          </div>
          <button
            className="btn-primary"
            onClick={() => setOutletModal({ show: true, outlet: null })}
          >
            <Plus size={16} />
            Add Outlet
          </button>
        </div>

        {loadingOutlets ? (
          <div className="loading-state">Loading outlets...</div>
        ) : outlets.length === 0 ? (
          <div className="empty-state">
            <p>No outlets configured. Click "Add Outlet" to get started.</p>
          </div>
        ) : (
          <div className="outlets-container">
            {sortedTypes.map(type => (
              <div key={type} className="outlet-type-group">
                <h3 className="outlet-type-header">{type}</h3>
                <div className="outlet-table">
                  <div className="outlet-table-header">
                    <span className="col-name">Name</span>
                    <span className="col-full-name">Full Name</span>
                    <span className="col-monitoring">Daily Monitoring</span>
                    <span className="col-actions">Actions</span>
                  </div>
                  {outletsByType[type].map(outlet => {
                    const monitoringSummary = getMonitoringSummary(outlet);
                    return (
                      <div key={outlet.id} className="outlet-table-row">
                        <span className="col-name outlet-tag">{outlet.name}</span>
                        <span className="col-full-name">{outlet.full_name || '—'}</span>
                        <span className="col-monitoring">
                          {monitoringSummary ? (
                            <span className="outlet-monitoring-badge enabled">
                              <Thermometer size={12} />
                              {monitoringSummary}
                            </span>
                          ) : (
                            <span className="outlet-monitoring-badge disabled">Off</span>
                          )}
                        </span>
                        <span className="col-actions">
                          {outlet.daily_monitoring_enabled && (
                            <button
                              className="btn-icon"
                              onClick={() => handleShowQr(outlet)}
                              title="Daily Log QR Code"
                            >
                              <QrCode size={16} />
                            </button>
                          )}
                          <button
                            className="btn-icon"
                            onClick={() => setOutletModal({ show: true, outlet })}
                            title="Edit outlet"
                          >
                            <Edit2 size={16} />
                          </button>
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* EHC Contacts */}
      <section className="settings-section">
        <div className="section-header">
          <div>
            <h2>EHC Contacts</h2>
            <p className="section-description">
              Manage people responsible for EHC at each outlet. Primary contacts receive automated QR code emails.
            </p>
          </div>
          <button
            className="btn-primary"
            onClick={() => setContactModal({ show: true, contact: null })}
          >
            <Plus size={16} />
            Add Contact
          </button>
        </div>

        {loadingContacts ? (
          <div className="loading-state">Loading contacts...</div>
        ) : contacts.length === 0 ? (
          <div className="empty-state">
            <p>No contacts configured. Click "Add Contact" to get started.</p>
          </div>
        ) : (
          <div className="contacts-table">
            <div className="contacts-table-header">
              <span className="col-name">Name</span>
              <span className="col-email">Email</span>
              <span className="col-title">Title</span>
              <span className="col-outlets">Outlets</span>
              <span className="col-actions">Actions</span>
            </div>
            {contacts.map(contact => (
              <div key={contact.id} className="contacts-table-row">
                <span className="col-name">{contact.name}</span>
                <span className="col-email">
                  <a href={`mailto:${contact.email}`}>{contact.email}</a>
                </span>
                <span className="col-title">{contact.title || '—'}</span>
                <span className="col-outlets">
                  {contact.outlets?.length > 0 ? (
                    <div className="outlet-pills">
                      {contact.outlets.map(o => (
                        <span
                          key={o.outlet_id}
                          className={`outlet-pill ${o.is_primary ? 'is-primary' : ''}`}
                          title={o.is_primary ? `Primary contact for ${o.outlet_name}` : o.outlet_name}
                        >
                          {o.outlet_name}
                          {o.is_primary && <Check size={10} />}
                        </span>
                      ))}
                    </div>
                  ) : (
                    <span className="text-muted">No outlets assigned</span>
                  )}
                </span>
                <span className="col-actions">
                  <button
                    className="btn-icon"
                    onClick={() => setContactModal({ show: true, contact })}
                    title="Edit contact"
                  >
                    <Edit2 size={16} />
                  </button>
                </span>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Email Configuration */}
      <section className="settings-section">
        <div className="section-header">
          <div>
            <h2>Email Configuration</h2>
            <p className="section-description">
              Email integration for sending QR codes and form links to contacts.
            </p>
          </div>
        </div>

        <div className="email-config-card">
          {/* Status */}
          <div className="email-status-row">
            <div className="email-status-indicator">
              {loadingEmailStatus ? (
                <span className="status-loading">Checking...</span>
              ) : emailStatus?.configured ? (
                <>
                  <CheckCircle size={20} className="status-icon success" />
                  <span className="status-text success">Email configured</span>
                </>
              ) : (
                <>
                  <AlertCircle size={20} className="status-icon warning" />
                  <span className="status-text warning">Email not configured</span>
                </>
              )}
            </div>

            {emailStatus?.configured && (
              <button
                className="btn-secondary"
                onClick={handleSendTestEmail}
                disabled={sendingTestEmail}
              >
                <Send size={16} />
                {sendingTestEmail ? 'Sending...' : 'Send Test Email'}
              </button>
            )}
          </div>

          {emailStatus?.sender && (
            <div className="email-detail">
              <span className="email-detail-label">Sender:</span>
              <span className="email-detail-value">{emailStatus.sender}</span>
            </div>
          )}

          {emailStatus?.error && !emailStatus?.configured && (
            <div className="email-detail warning">
              <span className="email-detail-label">Status:</span>
              <span className="email-detail-value">{emailStatus.error}</span>
            </div>
          )}
        </div>

        {/* Recent Emails */}
        {emailStatus?.configured && (
          <div className="email-log-section">
            <h3>Recent Emails</h3>
            {loadingEmailLog ? (
              <div className="loading-state">Loading email log...</div>
            ) : emailLog.length === 0 ? (
              <div className="empty-state small">
                <p>No emails sent yet.</p>
              </div>
            ) : (
              <div className="email-log-table">
                <div className="email-log-header">
                  <span className="col-recipient">Recipient</span>
                  <span className="col-subject">Subject</span>
                  <span className="col-type">Type</span>
                  <span className="col-status">Status</span>
                  <span className="col-date">Sent</span>
                </div>
                {emailLog.map(log => (
                  <div key={log.id} className="email-log-row">
                    <span className="col-recipient">
                      {log.email_to_name || log.email_to}
                    </span>
                    <span className="col-subject" title={log.email_subject}>
                      {log.email_subject?.length > 40
                        ? log.email_subject.substring(0, 40) + '...'
                        : log.email_subject}
                    </span>
                    <span className="col-type">
                      <span className={`type-badge ${log.email_type}`}>
                        {log.email_type === 'form_qr' ? 'Form QR' : log.email_type}
                      </span>
                    </span>
                    <span className="col-status">
                      <span className={`status-badge-sm ${log.status}`}>
                        {log.status === 'sent' && <Check size={12} />}
                        {log.status === 'failed' && <X size={12} />}
                        {log.status === 'pending' && <Clock size={12} />}
                        {log.status}
                      </span>
                    </span>
                    <span className="col-date">
                      {new Date(log.sent_at).toLocaleDateString()}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </section>

      {/* Responsibility Codes */}
      <section className="settings-section">
        <div className="section-header">
          <div>
            <h2>Responsibility Codes</h2>
            <p className="section-description">
              Define responsibility codes used in audit point assignments and record filtering.
              You define what each code means for your organization.
            </p>
          </div>
        </div>

        {loadingCodes ? (
          <div className="loading-state">Loading responsibility codes...</div>
        ) : respCodes.length === 0 ? (
          <div className="empty-state">
            <p>No responsibility codes configured. These will be used for audit tracking.</p>
          </div>
        ) : (
          <div className="resp-codes-table">
            <div className="resp-codes-header">
              <span className="col-code">Code</span>
              <span className="col-role">Role</span>
              <span className="col-scope">Scope</span>
              <span className="col-actions">Actions</span>
            </div>
            {respCodes.map(code => (
              <div key={code.id} className="resp-codes-row">
                <span className="col-code code-badge">{code.code}</span>
                {editingCodeId === code.id ? (
                  <>
                    <input
                      type="text"
                      className="col-role edit-input"
                      value={codeEditData.role_name ?? code.role_name ?? ''}
                      onChange={(e) => setCodeEditData({ ...codeEditData, role_name: e.target.value })}
                      placeholder="e.g., Audit Prep Manager"
                    />
                    <input
                      type="text"
                      className="col-scope edit-input"
                      value={codeEditData.scope ?? code.scope ?? ''}
                      onChange={(e) => setCodeEditData({ ...codeEditData, scope: e.target.value })}
                      placeholder="e.g., Coordination, swabbing"
                    />
                    <span className="col-actions">
                      <button
                        className="btn-sm btn-success"
                        onClick={() => handleUpdateRespCode(code.id, codeEditData)}
                      >
                        Save
                      </button>
                      <button
                        className="btn-sm btn-ghost"
                        onClick={() => {
                          setEditingCodeId(null);
                          setCodeEditData({});
                        }}
                      >
                        Cancel
                      </button>
                    </span>
                  </>
                ) : (
                  <>
                    <span className="col-role">{code.role_name || <em className="text-muted">Not defined</em>}</span>
                    <span className="col-scope">{code.scope || <em className="text-muted">Not defined</em>}</span>
                    <span className="col-actions">
                      <button
                        className="btn-icon"
                        onClick={() => {
                          setEditingCodeId(code.id);
                          setCodeEditData({ role_name: code.role_name, scope: code.scope });
                        }}
                        title="Edit code"
                      >
                        <Edit2 size={16} />
                      </button>
                      <button
                        className="btn-icon btn-danger-ghost"
                        onClick={() => handleDeleteRespCode(code.id)}
                        title="Deactivate code"
                      >
                        <X size={16} />
                      </button>
                    </span>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      {/* Outlet Modal */}
      {outletModal.show && (
        <OutletModal
          outlet={outletModal.outlet}
          outletTypes={outletTypes}
          onSave={handleSaveOutlet}
          onDelete={handleDeleteOutlet}
          onClose={() => setOutletModal({ show: false, outlet: null })}
        />
      )}

      {/* Contact Modal */}
      {contactModal.show && (
        <ContactModal
          contact={contactModal.contact}
          onSave={handleSaveContact}
          onDelete={handleDeleteContact}
          onClose={() => setContactModal({ show: false, contact: null })}
        />
      )}

      {/* Daily Log QR Code Modal */}
      {qrModal.show && (
        <div className="modal-overlay" onClick={closeQrModal}>
          <div className="modal-container modal-sm" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2>Daily Log QR Code</h2>
              <button className="modal-close" onClick={closeQrModal}>
                <X size={20} />
              </button>
            </div>

            <div className="modal-body qr-modal-body">
              <div className="qr-outlet-info">
                <span className="outlet-tag">{qrModal.outlet?.name}</span>
                <span className="outlet-name">{qrModal.outlet?.full_name}</span>
              </div>

              {!qrModal.outlet?.daily_log_token && !loadingQr && !generatingToken ? (
                <div className="qr-empty-state">
                  <QrCode size={48} className="qr-placeholder-icon" />
                  <p>No access link generated yet.</p>
                  <p className="text-muted">
                    Generate a QR code so staff can access the daily log without logging in.
                  </p>
                  <button
                    className="btn-primary"
                    onClick={handleGenerateToken}
                    disabled={generatingToken}
                  >
                    <QrCode size={16} />
                    Generate QR Code
                  </button>
                </div>
              ) : loadingQr || generatingToken ? (
                <div className="qr-loading">
                  <RefreshCw size={24} className="spinning" />
                  <span>{generatingToken ? 'Generating...' : 'Loading...'}</span>
                </div>
              ) : qrData ? (
                <div className="qr-display">
                  <img src={qrData} alt="Daily Log QR Code" className="qr-image" />
                  <p className="qr-instructions">
                    Staff can scan this code to access the daily worksheet for{' '}
                    <strong>{qrModal.outlet?.name}</strong> without logging in.
                  </p>
                </div>
              ) : null}
            </div>

            {qrData && (
              <div className="modal-footer">
                <button
                  className="btn-ghost"
                  onClick={handleGenerateToken}
                  disabled={generatingToken}
                  title="Generate a new link (invalidates old one)"
                >
                  <RefreshCw size={16} />
                  Regenerate
                </button>
                <button
                  className="btn-primary"
                  onClick={handleDownloadQr}
                >
                  <Download size={16} />
                  Download
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
