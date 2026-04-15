/**
 * Cooler Temperature Section
 *
 * Record 3: Cooler/freezer temperature logging with AM/PM shifts.
 * - Stepper UI for touch-friendly temp entry (starts at threshold edge)
 * - Auto-threshold check on change
 * - Inline corrective action when flagged
 * - Per-shift signature at bottom
 */

import { useState, useRef } from 'react';
import {
  Thermometer, AlertTriangle, Check, X, Minus, Plus
} from 'lucide-react';
import SignaturePad from 'react-signature-canvas';

export default function CoolerTempSection({
  outlet,
  readings,
  worksheetStatus,
  onReadingUpdate,
  onSignShift
}) {
  const [expandedFlagged, setExpandedFlagged] = useState(new Set());
  const [signingShift, setSigningShift] = useState(null);
  const [signerName, setSignerName] = useState('');
  const sigPadRef = useRef(null);

  const isLocked = worksheetStatus === 'approved';

  // Organize readings by unit
  const coolerReadings = readings.filter(r => r.unit_type === 'cooler');
  const freezerReadings = readings.filter(r => r.unit_type === 'freezer');

  // Check if shifts are signed
  const amReadings = readings.filter(r => r.shift === 'am');
  const pmReadings = readings.filter(r => r.shift === 'pm');
  const amSigned = amReadings.some(r => r.signature_data);
  const pmSigned = pmReadings.some(r => r.signature_data);

  // Get threshold for display
  const coolerMax = outlet?.cooler_max_f || 41.0;
  const freezerMax = outlet?.freezer_max_f || 0.0;

  function getReading(unitType, unitNumber, shift) {
    return readings.find(
      r => r.unit_type === unitType && r.unit_number === unitNumber && r.shift === shift
    );
  }

  function handleTempChange(unitType, unitNumber, shift, value) {
    const numValue = value === null ? null : parseFloat(value);
    onReadingUpdate(unitType, unitNumber, shift, {
      temperature_f: numValue
    });
  }

  // Stepper: increment/decrement by 0.1°F
  // If no value yet, initialize at threshold edge
  function handleTempStep(unitType, unitNumber, shift, direction, threshold) {
    const reading = getReading(unitType, unitNumber, shift);
    const currentValue = reading?.temperature_f;

    if (currentValue === null || currentValue === undefined) {
      // First tap: start at threshold (edge of danger zone)
      handleTempChange(unitType, unitNumber, shift, threshold);
    } else {
      // Subsequent taps: step by 0.1°F
      const newValue = Math.round((currentValue + (direction * 0.1)) * 10) / 10;
      handleTempChange(unitType, unitNumber, shift, newValue);
    }
  }

  function handleCorrectiveAction(unitType, unitNumber, shift, value) {
    onReadingUpdate(unitType, unitNumber, shift, {
      corrective_action: value
    });
  }

  function toggleFlagged(readingId) {
    setExpandedFlagged(prev => {
      const next = new Set(prev);
      if (next.has(readingId)) {
        next.delete(readingId);
      } else {
        next.add(readingId);
      }
      return next;
    });
  }

  function startSigning(shift) {
    setSigningShift(shift);
    setSignerName('');
  }

  function cancelSigning() {
    setSigningShift(null);
    setSignerName('');
    if (sigPadRef.current) {
      sigPadRef.current.clear();
    }
  }

  function submitSignature() {
    if (!signerName.trim()) {
      alert('Please enter your name');
      return;
    }
    if (sigPadRef.current?.isEmpty()) {
      alert('Please provide your signature');
      return;
    }

    const signatureData = sigPadRef.current.toDataURL('image/png');
    onSignShift(signingShift, signerName.trim(), signatureData);
    setSigningShift(null);
    setSignerName('');
  }

  function renderReadingRow(unitType, unitNumber, label, threshold) {
    const amReading = getReading(unitType, unitNumber, 'am');
    const pmReading = getReading(unitType, unitNumber, 'pm');

    return (
      <div key={`${unitType}-${unitNumber}`} className="reading-row">
        <div className="unit-label">
          <Thermometer size={16} />
          <span>{label}</span>
        </div>

        {/* AM Reading */}
        <div className={`reading-cell ${amReading?.is_flagged ? 'flagged' : ''}`} data-shift="AM">
          <div className="temp-stepper">
            <button
              className="stepper-btn"
              onClick={() => handleTempStep(unitType, unitNumber, 'am', -1, threshold)}
              disabled={isLocked || amSigned}
              aria-label="Decrease temperature"
            >
              <Minus size={18} />
            </button>
            <span className={`temp-display ${amReading?.temperature_f != null ? 'has-value' : 'placeholder'}`}>
              {amReading?.temperature_f != null ? `${amReading.temperature_f}°` : `${threshold}°`}
            </span>
            <button
              className="stepper-btn"
              onClick={() => handleTempStep(unitType, unitNumber, 'am', 1, threshold)}
              disabled={isLocked || amSigned}
              aria-label="Increase temperature"
            >
              <Plus size={18} />
            </button>
          </div>
          {amReading?.is_flagged && (
            <button
              className="flag-btn"
              onClick={() => toggleFlagged(amReading.id)}
              title="View/add corrective action"
            >
              <AlertTriangle size={14} />
            </button>
          )}
          {amReading?.signature_data && (
            <Check size={14} className="signed-icon" title="Signed" />
          )}
        </div>

        {/* PM Reading */}
        <div className={`reading-cell ${pmReading?.is_flagged ? 'flagged' : ''}`} data-shift="PM">
          <div className="temp-stepper">
            <button
              className="stepper-btn"
              onClick={() => handleTempStep(unitType, unitNumber, 'pm', -1, threshold)}
              disabled={isLocked || pmSigned}
              aria-label="Decrease temperature"
            >
              <Minus size={18} />
            </button>
            <span className={`temp-display ${pmReading?.temperature_f != null ? 'has-value' : 'placeholder'}`}>
              {pmReading?.temperature_f != null ? `${pmReading.temperature_f}°` : `${threshold}°`}
            </span>
            <button
              className="stepper-btn"
              onClick={() => handleTempStep(unitType, unitNumber, 'pm', 1, threshold)}
              disabled={isLocked || pmSigned}
              aria-label="Increase temperature"
            >
              <Plus size={18} />
            </button>
          </div>
          {pmReading?.is_flagged && (
            <button
              className="flag-btn"
              onClick={() => toggleFlagged(pmReading.id)}
              title="View/add corrective action"
            >
              <AlertTriangle size={14} />
            </button>
          )}
          {pmReading?.signature_data && (
            <Check size={14} className="signed-icon" title="Signed" />
          )}
        </div>

        <div className="threshold-cell">
          <span className="threshold-label">max {threshold}°F</span>
        </div>

        {/* Corrective Action Expansion */}
        {(expandedFlagged.has(amReading?.id) || expandedFlagged.has(pmReading?.id)) && (
          <div className="corrective-action-row">
            {expandedFlagged.has(amReading?.id) && amReading && (
              <div className="corrective-action-input">
                <span className="ca-label">AM Corrective Action:</span>
                <textarea
                  value={amReading.corrective_action || ''}
                  onChange={(e) => handleCorrectiveAction(unitType, unitNumber, 'am', e.target.value)}
                  placeholder="Describe the issue and action taken..."
                  disabled={isLocked || amSigned}
                />
              </div>
            )}
            {expandedFlagged.has(pmReading?.id) && pmReading && (
              <div className="corrective-action-input">
                <span className="ca-label">PM Corrective Action:</span>
                <textarea
                  value={pmReading.corrective_action || ''}
                  onChange={(e) => handleCorrectiveAction(unitType, unitNumber, 'pm', e.target.value)}
                  placeholder="Describe the issue and action taken..."
                  disabled={isLocked || pmSigned}
                />
              </div>
            )}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="temp-section">
      <div className="section-header">
        <h2>
          <Thermometer size={20} />
          Cooler & Freezer Temperatures
        </h2>
        <span className="record-badge">Record 3</span>
      </div>

      {/* Reading Grid */}
      <div className="readings-grid">
        <div className="grid-header">
          <span className="col-unit">Unit</span>
          <span className="col-temp">AM</span>
          <span className="col-temp">PM</span>
          <span className="col-threshold">Threshold</span>
        </div>

        {/* Coolers */}
        {coolerReadings.length > 0 && (
          <div className="unit-group">
            <div className="group-label">Coolers</div>
            {Array.from({ length: outlet?.cooler_count || 0 }, (_, i) =>
              renderReadingRow('cooler', i + 1, `Cooler ${i + 1}`, coolerMax)
            )}
          </div>
        )}

        {/* Freezers */}
        {freezerReadings.length > 0 && (
          <div className="unit-group">
            <div className="group-label">Freezers</div>
            {Array.from({ length: outlet?.freezer_count || 0 }, (_, i) =>
              renderReadingRow('freezer', i + 1, `Freezer ${i + 1}`, freezerMax)
            )}
          </div>
        )}
      </div>

      {/* Signature Section */}
      <div className="signature-section">
        <h3>Shift Signatures</h3>

        <div className="signature-buttons">
          {/* AM Signature */}
          <div className={`signature-slot ${amSigned ? 'signed' : ''}`}>
            {amSigned ? (
              <div className="signed-info">
                <Check size={16} />
                <span>AM Signed</span>
              </div>
            ) : (
              <button
                className="btn-secondary"
                onClick={() => startSigning('am')}
                disabled={isLocked || signingShift !== null}
              >
                Sign AM Shift
              </button>
            )}
          </div>

          {/* PM Signature */}
          <div className={`signature-slot ${pmSigned ? 'signed' : ''}`}>
            {pmSigned ? (
              <div className="signed-info">
                <Check size={16} />
                <span>PM Signed</span>
              </div>
            ) : (
              <button
                className="btn-secondary"
                onClick={() => startSigning('pm')}
                disabled={isLocked || signingShift !== null}
              >
                Sign PM Shift
              </button>
            )}
          </div>
        </div>

        {/* Signature Pad */}
        {signingShift && (
          <div className="signature-modal">
            <div className="signature-modal-content">
              <div className="signature-modal-header">
                <h4>Sign {signingShift.toUpperCase()} Shift</h4>
                <button className="close-btn" onClick={cancelSigning}>
                  <X size={20} />
                </button>
              </div>

              <div className="signature-form">
                <div className="form-group">
                  <label>Your Name / Initials</label>
                  <input
                    type="text"
                    className="input"
                    value={signerName}
                    onChange={(e) => setSignerName(e.target.value)}
                    placeholder="Enter your name"
                    autoFocus
                  />
                </div>

                <div className="form-group">
                  <label>Signature</label>
                  <div className="signature-pad-container">
                    <SignaturePad
                      ref={sigPadRef}
                      canvasProps={{
                        className: 'signature-canvas'
                      }}
                    />
                  </div>
                  <button
                    className="btn-ghost btn-sm"
                    onClick={() => sigPadRef.current?.clear()}
                  >
                    Clear
                  </button>
                </div>
              </div>

              <div className="signature-modal-footer">
                <button className="btn-ghost" onClick={cancelSigning}>
                  Cancel
                </button>
                <button className="btn-primary" onClick={submitSignature}>
                  <Check size={16} />
                  Submit Signature
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
