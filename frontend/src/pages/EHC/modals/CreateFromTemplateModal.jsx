import { useState, useEffect } from 'react';
import { X, Check, ChevronRight, QrCode, ClipboardList, Building2 } from 'lucide-react';
import { fetchWithAuth, API_BASE } from '../tabs/shared';
import './CreateFromTemplateModal.css';

/**
 * Create From Template Modal
 *
 * Deploys a form template to multiple outlets at once.
 * Steps:
 * 1. Select template
 * 2. Select outlets
 * 3. Set period label
 * 4. Review and create
 */
export default function CreateFromTemplateModal({
  isOpen,
  onClose,
  activeCycle,
  onFormsCreated,
  toast
}) {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [deploying, setDeploying] = useState(false);

  // Data
  const [templates, setTemplates] = useState([]);
  const [outlets, setOutlets] = useState([]);

  // Selections
  const [selectedTemplate, setSelectedTemplate] = useState(null);
  const [selectedOutlets, setSelectedOutlets] = useState([]);
  const [periodLabel, setPeriodLabel] = useState('');
  const [customOutlet, setCustomOutlet] = useState('');

  // Results
  const [createdForms, setCreatedForms] = useState([]);

  // Load templates and outlets when modal opens
  useEffect(() => {
    if (isOpen && activeCycle?.id) {
      loadTemplates();
      loadOutlets();
      // Reset state
      setStep(1);
      setSelectedTemplate(null);
      setSelectedOutlets([]);
      setPeriodLabel(getDefaultPeriodLabel());
      setCreatedForms([]);
    }
  }, [isOpen, activeCycle?.id]);

  function getDefaultPeriodLabel() {
    const now = new Date();
    const monthNames = ['January', 'February', 'March', 'April', 'May', 'June',
      'July', 'August', 'September', 'October', 'November', 'December'];
    return `${monthNames[now.getMonth()]} ${now.getFullYear()}`;
  }

  async function loadTemplates() {
    try {
      setLoading(true);
      const data = await fetchWithAuth(`${API_BASE}/templates`);
      setTemplates(data.data || []);
    } catch (error) {
      console.error('Failed to load templates:', error);
      toast?.error?.('Failed to load templates');
    } finally {
      setLoading(false);
    }
  }

  async function loadOutlets() {
    try {
      const data = await fetchWithAuth(`${API_BASE}/outlets`);
      setOutlets(data.data || []);
    } catch (error) {
      console.error('Failed to load outlets:', error);
      // Non-fatal - outlets can be entered manually
    }
  }

  function toggleOutlet(outletName) {
    setSelectedOutlets(prev => {
      if (prev.includes(outletName)) {
        return prev.filter(o => o !== outletName);
      } else {
        return [...prev, outletName];
      }
    });
  }

  function addCustomOutlet() {
    const name = customOutlet.trim();
    if (name && !selectedOutlets.includes(name)) {
      setSelectedOutlets(prev => [...prev, name]);
      setCustomOutlet('');
    }
  }

  async function handleDeploy() {
    if (!selectedTemplate || selectedOutlets.length === 0 || !periodLabel.trim()) {
      return;
    }

    try {
      setDeploying(true);
      const response = await fetchWithAuth(`${API_BASE}/templates/${selectedTemplate.id}/deploy`, {
        method: 'POST',
        body: JSON.stringify({
          outlets: selectedOutlets,
          period_label: periodLabel.trim()
        })
      });

      setCreatedForms(response.forms || []);
      setStep(4); // Success step
      toast?.success?.(`Created ${response.forms_created} form links`);
    } catch (error) {
      console.error('Failed to deploy template:', error);
      toast?.error?.(error.message || 'Failed to create forms');
    } finally {
      setDeploying(false);
    }
  }

  function handleClose() {
    if (createdForms.length > 0) {
      onFormsCreated?.();
    }
    onClose();
  }

  function copyToClipboard(text) {
    navigator.clipboard.writeText(text);
    toast?.success?.('Copied to clipboard');
  }

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="create-template-modal" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <h2>Create from Template</h2>
          <button className="btn-close" onClick={handleClose}>
            <X size={20} />
          </button>
        </div>

        {/* Progress Steps */}
        <div className="step-progress">
          <div className={`step ${step >= 1 ? 'active' : ''} ${step > 1 ? 'complete' : ''}`}>
            <span className="step-number">1</span>
            <span className="step-label">Template</span>
          </div>
          <div className="step-connector" />
          <div className={`step ${step >= 2 ? 'active' : ''} ${step > 2 ? 'complete' : ''}`}>
            <span className="step-number">2</span>
            <span className="step-label">Outlets</span>
          </div>
          <div className="step-connector" />
          <div className={`step ${step >= 3 ? 'active' : ''} ${step > 3 ? 'complete' : ''}`}>
            <span className="step-number">3</span>
            <span className="step-label">Review</span>
          </div>
        </div>

        {/* Step Content */}
        <div className="modal-content">
          {/* Step 1: Select Template */}
          {step === 1 && (
            <div className="step-content">
              <h3>Select a Template</h3>
              <p className="step-description">
                Choose a form template to deploy. Each template defines the questions and settings.
              </p>

              {loading ? (
                <div className="loading-state">Loading templates...</div>
              ) : templates.length === 0 ? (
                <div className="empty-state">
                  <ClipboardList size={40} />
                  <p>No templates available</p>
                  <span>Templates will appear here once seeded</span>
                </div>
              ) : (
                <div className="template-list">
                  {templates.map(template => (
                    <div
                      key={template.id}
                      className={`template-card ${selectedTemplate?.id === template.id ? 'selected' : ''}`}
                      onClick={() => setSelectedTemplate(template)}
                    >
                      <div className="template-icon">
                        <ClipboardList size={24} />
                      </div>
                      <div className="template-info">
                        <h4>{template.name}</h4>
                        <div className="template-meta">
                          <span>{template.item_count} questions</span>
                          {template.record_number && (
                            <span>Record {template.record_number}</span>
                          )}
                        </div>
                      </div>
                      {selectedTemplate?.id === template.id && (
                        <div className="selected-indicator">
                          <Check size={18} />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Step 2: Select Outlets */}
          {step === 2 && (
            <div className="step-content">
              <h3>Select Outlets</h3>
              <p className="step-description">
                Choose which outlets should receive this checklist. Each outlet gets its own QR code.
              </p>

              <div className="period-input">
                <label>Period Label</label>
                <input
                  type="text"
                  value={periodLabel}
                  onChange={e => setPeriodLabel(e.target.value)}
                  placeholder="e.g., April 2026"
                />
              </div>

              {outlets.length > 0 && (
                <div className="outlet-chips">
                  {outlets.map(outlet => (
                    <button
                      key={outlet.id || outlet.name}
                      type="button"
                      className={`outlet-chip ${selectedOutlets.includes(outlet.name) ? 'selected' : ''}`}
                      onClick={() => toggleOutlet(outlet.name)}
                    >
                      {selectedOutlets.includes(outlet.name) && <Check size={14} />}
                      {outlet.name}
                    </button>
                  ))}
                </div>
              )}

              <div className="custom-outlet">
                <label>Add Custom Outlet</label>
                <div className="custom-outlet-input">
                  <input
                    type="text"
                    value={customOutlet}
                    onChange={e => setCustomOutlet(e.target.value)}
                    placeholder="Enter outlet name"
                    onKeyDown={e => e.key === 'Enter' && addCustomOutlet()}
                  />
                  <button
                    type="button"
                    onClick={addCustomOutlet}
                    disabled={!customOutlet.trim()}
                  >
                    Add
                  </button>
                </div>
              </div>

              {selectedOutlets.length > 0 && (
                <div className="selected-outlets">
                  <label>Selected ({selectedOutlets.length})</label>
                  <div className="selected-outlet-tags">
                    {selectedOutlets.map(name => (
                      <span key={name} className="outlet-tag">
                        {name}
                        <button onClick={() => toggleOutlet(name)}>
                          <X size={12} />
                        </button>
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 3: Review */}
          {step === 3 && (
            <div className="step-content">
              <h3>Review & Create</h3>
              <p className="step-description">
                Confirm the details below. This will create {selectedOutlets.length} form link{selectedOutlets.length !== 1 ? 's' : ''}.
              </p>

              <div className="review-summary">
                <div className="review-item">
                  <span className="review-label">Template</span>
                  <span className="review-value">{selectedTemplate?.name}</span>
                </div>
                <div className="review-item">
                  <span className="review-label">Questions</span>
                  <span className="review-value">{selectedTemplate?.item_count}</span>
                </div>
                <div className="review-item">
                  <span className="review-label">Period</span>
                  <span className="review-value">{periodLabel}</span>
                </div>
                <div className="review-item">
                  <span className="review-label">Outlets</span>
                  <div className="review-outlets">
                    {selectedOutlets.map(name => (
                      <span key={name} className="outlet-badge">{name}</span>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Success */}
          {step === 4 && (
            <div className="step-content success">
              <div className="success-icon">
                <Check size={40} />
              </div>
              <h3>Forms Created!</h3>
              <p className="step-description">
                Created {createdForms.length} form links. Each outlet has a unique QR code.
              </p>

              <div className="created-forms-list">
                {createdForms.map(form => (
                  <div key={form.form_link_id} className="created-form-item">
                    <div className="form-outlet">
                      <Building2 size={16} />
                      <span>{form.outlet_name}</span>
                    </div>
                    <div className="form-actions">
                      <button
                        type="button"
                        className="btn-copy-link"
                        onClick={() => copyToClipboard(form.url)}
                        title="Copy link"
                      >
                        Copy Link
                      </button>
                      {form.qr_code && (
                        <img
                          src={`data:image/png;base64,${form.qr_code}`}
                          alt={`QR for ${form.outlet_name}`}
                          className="qr-preview"
                        />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="modal-footer">
          {step < 4 && (
            <>
              {step > 1 && (
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => setStep(s => s - 1)}
                  disabled={deploying}
                >
                  Back
                </button>
              )}
              <div className="footer-spacer" />
              {step < 3 ? (
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => setStep(s => s + 1)}
                  disabled={
                    (step === 1 && !selectedTemplate) ||
                    (step === 2 && (selectedOutlets.length === 0 || !periodLabel.trim()))
                  }
                >
                  Continue
                  <ChevronRight size={18} />
                </button>
              ) : (
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleDeploy}
                  disabled={deploying}
                >
                  {deploying ? 'Creating...' : `Create ${selectedOutlets.length} Form${selectedOutlets.length !== 1 ? 's' : ''}`}
                </button>
              )}
            </>
          )}
          {step === 4 && (
            <button
              type="button"
              className="btn-primary"
              onClick={handleClose}
            >
              Done
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
