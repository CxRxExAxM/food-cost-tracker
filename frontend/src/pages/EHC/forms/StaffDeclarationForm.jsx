import { useState, useRef, useCallback, useEffect } from 'react';
import SignaturePad from './SignaturePad';
import { RECORD_11 } from './templates/record_11';
import './StaffDeclarationForm.css';

/**
 * Staff Declaration Form (Record 11)
 *
 * Features:
 * - Displays full declaration content
 * - Scroll-to-sign gate: sign section disabled until scrolled to bottom
 * - Acknowledgment checkbox
 * - Name input + signature pad
 */
export default function StaffDeclarationForm({
  config,
  existingResponses = [],
  onSubmit,
  submitting = false
}) {
  const [hasScrolledToBottom, setHasScrolledToBottom] = useState(false);
  const [acknowledged, setAcknowledged] = useState(false);
  const [name, setName] = useState('');
  const [outlet, setOutlet] = useState('');
  const [signature, setSignature] = useState(null);
  const [duplicateWarning, setDuplicateWarning] = useState(null);

  // Outlets from config or placeholder list
  const outlets = config?.outlets || [
    'La Hacienda',
    'Toro Latin Kitchen',
    'Bourbon Steak',
    'The Plaza Bar',
    'Ironwood American Kitchen',
    'Banquets / Catering',
    'Stewarding',
    'Culinary Admin'
  ];

  const declarationRef = useRef(null);

  // Check for existing response when name changes
  useEffect(() => {
    if (name.trim().length < 2) {
      setDuplicateWarning(null);
      return;
    }

    const existing = existingResponses.find(
      r => r.respondent_name.toLowerCase().trim() === name.toLowerCase().trim()
    );

    if (existing) {
      const date = new Date(existing.submitted_at).toLocaleDateString();
      setDuplicateWarning({
        name: existing.respondent_name,
        date
      });
    } else {
      setDuplicateWarning(null);
    }
  }, [name, existingResponses]);

  // Track scroll position to enable sign section
  const handleScroll = useCallback((e) => {
    const element = e.target;
    const scrolledToBottom =
      element.scrollHeight - element.scrollTop <= element.clientHeight + 50;

    if (scrolledToBottom && !hasScrolledToBottom) {
      setHasScrolledToBottom(true);
    }
  }, [hasScrolledToBottom]);

  const canSubmit = hasScrolledToBottom &&
    acknowledged &&
    name.trim().length >= 2 &&
    signature;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!canSubmit || submitting) return;

    onSubmit({
      respondent_name: name.trim(),
      respondent_dept: outlet || null,
      response_data: {
        acknowledged: true,
        scrolled_to_bottom: true,
        outlet: outlet || null
      },
      signature_data: signature
    });
  };

  const propertyName = config?.property_name || 'Property';
  const cycleYear = config?.cycle_year || new Date().getFullYear();

  return (
    <form className="staff-declaration-form" onSubmit={handleSubmit}>
      {/* Header */}
      <div className="form-header">
        <h1 className="form-title">{RECORD_11.title}</h1>
        <div className="form-meta">
          <span>{propertyName}</span>
          <span className="meta-divider">•</span>
          <span>EHC {cycleYear}</span>
        </div>
        <div className="form-version">{RECORD_11.version}</div>
      </div>

      {/* Declaration Content - Scrollable */}
      <div
        ref={declarationRef}
        className="declaration-content"
        onScroll={handleScroll}
      >
        {/* Intro paragraphs */}
        <div className="declaration-intro">
          {RECORD_11.intro.map((para, idx) => (
            <p key={idx}>{para}</p>
          ))}
        </div>

        {/* Numbered items */}
        <ol className="declaration-items">
          {RECORD_11.items.map((item, idx) => (
            <li key={idx}>{item}</li>
          ))}
        </ol>

        {/* Scroll prompt */}
        {!hasScrolledToBottom && (
          <div className="scroll-prompt">
            ↓ Scroll to read the full declaration before signing
          </div>
        )}
      </div>

      {/* Sign Section - Enabled after scrolling */}
      <div className={`sign-section ${hasScrolledToBottom ? 'enabled' : 'disabled'}`}>
        {!hasScrolledToBottom && (
          <div className="sign-overlay">
            <span>Please read the full declaration above to continue</span>
          </div>
        )}

        {/* Acknowledgment checkbox */}
        <label className="acknowledgment-checkbox">
          <input
            type="checkbox"
            checked={acknowledged}
            onChange={(e) => setAcknowledged(e.target.checked)}
            disabled={!hasScrolledToBottom}
          />
          <span>{RECORD_11.acknowledgmentText}</span>
        </label>

        {/* Name input */}
        <div className="form-field">
          <label htmlFor="respondent-name">Full Name</label>
          <input
            id="respondent-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Enter your full name"
            disabled={!hasScrolledToBottom}
            className="input"
          />
          {duplicateWarning && (
            <div className="duplicate-warning">
              A response for "{duplicateWarning.name}" was already submitted on {duplicateWarning.date}.
              Submitting will replace it.
            </div>
          )}
        </div>

        {/* Outlet selector */}
        <div className="form-field">
          <label htmlFor="respondent-outlet">Outlet / Department</label>
          <select
            id="respondent-outlet"
            value={outlet}
            onChange={(e) => setOutlet(e.target.value)}
            disabled={!hasScrolledToBottom}
            className="input select"
          >
            <option value="">Select your outlet...</option>
            {outlets.map((o, idx) => (
              <option key={idx} value={o}>{o}</option>
            ))}
          </select>
        </div>

        {/* Signature */}
        <div className="form-field">
          <SignaturePad
            onSignatureChange={setSignature}
            disabled={!hasScrolledToBottom}
          />
        </div>

        {/* Submit button */}
        <button
          type="submit"
          className="btn-submit"
          disabled={!canSubmit || submitting}
        >
          {submitting ? 'Submitting...' : 'Submit Declaration'}
        </button>
      </div>
    </form>
  );
}
