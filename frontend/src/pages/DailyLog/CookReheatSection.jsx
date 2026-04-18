/**
 * Cook/Reheat Section (Records 4 & 6)
 *
 * Cooking temperature logging by meal period.
 * - Grouped by meal period (breakfast/lunch/dinner)
 * - Entry types: cook, reheat, hot_hold, cold_hold
 * - Auto-flagging based on temperature thresholds
 * - Per-meal-period signature
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Flame, Plus, Trash2, AlertTriangle, Check, X, Clock
} from 'lucide-react';
import SignaturePad from 'react-signature-canvas';
import api from '../../lib/axios';
import { useToast } from '../../contexts/ToastContext';

const MEAL_PERIODS = ['breakfast', 'lunch', 'dinner'];
const SAVE_DEBOUNCE_MS = 1500;
const ENTRY_TYPES = [
  { id: 'cook', label: 'Cook' },
  { id: 'reheat', label: 'Reheat' },
  { id: 'hot_hold', label: 'Hot Hold' },
  { id: 'cold_hold', label: 'Cold Hold' }
];

export default function CookReheatSection({
  worksheet,
  outlet,
  records,
  setRecords,
  onSavingChange,
  publicToken  // Token for public (QR code) access - uses public API endpoints
}) {
  // Build API base path - uses public endpoint when accessed via QR code
  const apiBase = publicToken
    ? `/daily-log/public/${publicToken}`
    : `/daily-log/worksheet/${worksheet?.id}`;

  const [signingMeal, setSigningMeal] = useState(null);
  const [signerName, setSignerName] = useState('');
  const [addingTo, setAddingTo] = useState(null); // { mealPeriod, entryType }
  const sigPadRef = useRef(null);
  const toast = useToast();

  // Debounce state for auto-save
  const pendingChanges = useRef(new Map());
  const saveTimeoutRef = useRef(null);

  const isLocked = worksheet?.status === 'approved';

  // Group records by meal period
  const recordsByMeal = MEAL_PERIODS.reduce((acc, meal) => {
    acc[meal] = records.filter(r => r.meal_period === meal);
    return acc;
  }, {});

  // Check which meal periods are active
  const activeMeals = MEAL_PERIODS.filter(meal => {
    if (meal === 'breakfast' && outlet?.serves_breakfast) return true;
    if (meal === 'lunch' && outlet?.serves_lunch) return true;
    if (meal === 'dinner' && outlet?.serves_dinner) return true;
    return false;
  });

  // Check if meal period is signed
  function isMealSigned(meal) {
    return recordsByMeal[meal]?.some(r => r.signature_data);
  }

  // Get minimum entries required per meal
  const minEntries = outlet?.readings_per_service || 3;

  async function addRecord(mealPeriod, entryType) {
    if ((!worksheet && !publicToken) || isLocked) return;

    try {
      onSavingChange(true);
      const response = await api.post(`${apiBase}/cooking`, {
        meal_period: mealPeriod,
        entry_type: entryType
      });
      setRecords(prev => [...prev, response.data]);
      setAddingTo(null);
    } catch (err) {
      console.error('Error adding record:', err);
      toast.error(err.response?.data?.detail || 'Failed to add entry');
    } finally {
      onSavingChange(false);
    }
  }

  // Flush pending changes to server
  const flushPendingChanges = useCallback(async () => {
    if ((!worksheet && !publicToken) || pendingChanges.current.size === 0) return;

    onSavingChange(true);
    const changes = Array.from(pendingChanges.current.entries());
    pendingChanges.current.clear();

    try {
      for (const [recordId, updates] of changes) {
        const response = await api.put(
          `${apiBase}/cooking/${recordId}`,
          updates
        );
        setRecords(prev =>
          prev.map(r => r.id === recordId ? response.data : r)
        );
      }
    } catch (err) {
      console.error('Error updating record:', err);
      toast.error(err.response?.data?.detail || 'Failed to update');
    } finally {
      onSavingChange(false);
    }
  }, [worksheet, publicToken, apiBase, setRecords, onSavingChange, toast]);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  function updateRecord(recordId, updates) {
    if ((!worksheet && !publicToken) || isLocked) return;

    // Immediately update local state for responsive UI
    setRecords(prev =>
      prev.map(r => r.id === recordId ? { ...r, ...updates } : r)
    );

    // Merge with any pending changes for this record
    const existing = pendingChanges.current.get(recordId) || {};
    pendingChanges.current.set(recordId, { ...existing, ...updates });

    // Clear existing timeout and set new one
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    saveTimeoutRef.current = setTimeout(flushPendingChanges, SAVE_DEBOUNCE_MS);
  }

  async function deleteRecord(recordId) {
    if ((!worksheet && !publicToken) || isLocked) return;
    if (!confirm('Delete this entry?')) return;

    try {
      onSavingChange(true);
      await api.delete(`${apiBase}/cooking/${recordId}`);
      setRecords(prev => prev.filter(r => r.id !== recordId));
    } catch (err) {
      console.error('Error deleting record:', err);
      toast.error(err.response?.data?.detail || 'Failed to delete');
    } finally {
      onSavingChange(false);
    }
  }

  function startSigning(meal) {
    setSigningMeal(meal);
    setSignerName('');
  }

  function cancelSigning() {
    setSigningMeal(null);
    setSignerName('');
    if (sigPadRef.current) sigPadRef.current.clear();
  }

  async function submitSignature() {
    if (!signerName.trim()) {
      alert('Please enter your name');
      return;
    }
    if (sigPadRef.current?.isEmpty()) {
      alert('Please provide your signature');
      return;
    }

    try {
      onSavingChange(true);
      const signatureData = sigPadRef.current.toDataURL('image/png');
      await api.post(`${apiBase}/cooking/sign`, {
        meal_period: signingMeal,
        recorded_by: signerName.trim(),
        signature_data: signatureData
      });

      // Update local records with signature
      setRecords(prev =>
        prev.map(r =>
          r.meal_period === signingMeal
            ? { ...r, signature_data: signatureData, recorded_by: r.recorded_by || signerName.trim() }
            : r
        )
      );
      setSigningMeal(null);
      setSignerName('');
    } catch (err) {
      console.error('Error signing:', err);
      toast.error(err.response?.data?.detail || 'Failed to sign');
    } finally {
      onSavingChange(false);
    }
  }

  function renderMealPeriod(meal) {
    const mealRecords = recordsByMeal[meal] || [];
    const signed = isMealSigned(meal);
    const completedCount = mealRecords.filter(r => r.temperature_f != null).length;

    return (
      <div key={meal} className="meal-period-section">
        <div className="meal-header">
          <h3>{meal.charAt(0).toUpperCase() + meal.slice(1)}</h3>
          <div className="meal-stats">
            <span className={completedCount >= minEntries ? 'complete' : 'incomplete'}>
              {completedCount}/{minEntries} entries
            </span>
            {signed && <Check size={14} className="signed-icon" />}
          </div>
        </div>

        {/* Record entries */}
        <div className="cooking-entries">
          {mealRecords.map(record => (
            <div
              key={record.id}
              className={`cooking-entry ${record.is_flagged ? 'flagged' : ''}`}
            >
              <div className="entry-type-badge">
                {ENTRY_TYPES.find(t => t.id === record.entry_type)?.label || record.entry_type}
              </div>

              <input
                type="text"
                className="item-input"
                placeholder="Item name..."
                value={record.item_name || ''}
                onChange={(e) => updateRecord(record.id, { item_name: e.target.value })}
                disabled={isLocked || signed}
              />

              <div className="temp-time-row">
                <input
                  type="number"
                  step="0.1"
                  className="temp-input-sm"
                  placeholder="°F"
                  value={record.temperature_f ?? ''}
                  onChange={(e) => updateRecord(record.id, {
                    temperature_f: e.target.value ? parseFloat(e.target.value) : null
                  })}
                  disabled={isLocked || signed}
                />
                <input
                  type="time"
                  className="time-input"
                  value={record.time_recorded || ''}
                  onChange={(e) => updateRecord(record.id, { time_recorded: e.target.value })}
                  disabled={isLocked || signed}
                />
                {!signed && !isLocked && (
                  <button
                    className="delete-btn"
                    onClick={() => deleteRecord(record.id)}
                    title="Delete entry"
                  >
                    <Trash2 size={14} />
                  </button>
                )}
              </div>

              {record.is_flagged && (
                <div className="flagged-indicator">
                  <AlertTriangle size={12} />
                  <span>Below threshold</span>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Add entry buttons */}
        {!signed && !isLocked && (
          <div className="add-entry-row">
            {ENTRY_TYPES.map(type => (
              <button
                key={type.id}
                className="add-entry-btn"
                onClick={() => addRecord(meal, type.id)}
              >
                <Plus size={14} />
                {type.label}
              </button>
            ))}
          </div>
        )}

        {/* Sign button */}
        <div className="meal-signature">
          {signed ? (
            <div className="signed-info">
              <Check size={16} />
              <span>Signed</span>
            </div>
          ) : (
            <button
              className="btn-secondary"
              onClick={() => startSigning(meal)}
              disabled={isLocked || signingMeal !== null || completedCount === 0}
            >
              Sign {meal.charAt(0).toUpperCase() + meal.slice(1)}
            </button>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="cook-section">
      <div className="section-header">
        <h2>
          <Flame size={20} />
          Cook & Reheat Temperatures
        </h2>
        <span className="record-badge">Records 4 & 6</span>
      </div>

      <div className="meal-periods">
        {activeMeals.map(meal => renderMealPeriod(meal))}
      </div>

      {activeMeals.length === 0 && (
        <div className="empty-section">
          <p>No meal periods configured for this outlet.</p>
        </div>
      )}

      {/* Signature Modal */}
      {signingMeal && (
        <div className="signature-modal">
          <div className="signature-modal-content">
            <div className="signature-modal-header">
              <h4>Sign {signingMeal.charAt(0).toUpperCase() + signingMeal.slice(1)}</h4>
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
                    canvasProps={{ className: 'signature-canvas' }}
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
  );
}
