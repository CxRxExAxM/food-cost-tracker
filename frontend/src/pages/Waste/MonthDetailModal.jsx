import { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import axios from '../../lib/axios';
import './MonthDetailModal.css';

const MONTHS = ["January", "February", "March", "April", "May", "June",
               "July", "August", "September", "October", "November", "December"];

function MonthDetailModal({ year, month, goalTarget, onClose }) {
  const { user } = useAuth();
  const [metric, setMetric] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // Form state
  const [fbCovers, setFbCovers] = useState('');
  const [fteCount, setFteCount] = useState('');
  const [tempCount, setTempCount] = useState('');
  const [capturePercent, setCapturePercent] = useState('');
  const [donationLbs, setDonationLbs] = useState('');
  const [compostLbs, setCompostLbs] = useState('');
  const [notes, setNotes] = useState('');

  useEffect(() => {
    fetchMonthData();
  }, [year, month]);

  const fetchMonthData = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`/api/waste/metrics/${year}/${month}`);
      const data = response.data;
      setMetric(data);

      // Populate form fields
      setFbCovers(data.fb_covers !== null ? data.fb_covers : '');
      setFteCount(data.fte_count !== null ? data.fte_count : '');
      setTempCount(data.temp_count !== null ? data.temp_count : '');
      setCapturePercent(data.theoretic_capture_pct !== null ? data.theoretic_capture_pct : '');
      setDonationLbs(data.donation_lbs !== null ? data.donation_lbs : '');
      setCompostLbs(data.compost_lbs !== null ? data.compost_lbs : '');
      setNotes(data.notes || '');
    } catch (error) {
      console.error('Error fetching month data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const params = {
        fb_covers: fbCovers !== '' ? parseInt(fbCovers) : null,
        fte_count: fteCount !== '' ? parseInt(fteCount) : null,
        temp_count: tempCount !== '' ? parseInt(tempCount) : null,
        theoretic_capture_pct: capturePercent !== '' ? parseFloat(capturePercent) : null,
        donation_lbs: donationLbs !== '' ? parseFloat(donationLbs) : null,
        compost_lbs: compostLbs !== '' ? parseFloat(compostLbs) : null,
        notes: notes || null
      };

      await axios.put(`/api/waste/metrics/${year}/${month}`, null, { params });
      onClose(); // Close modal and refresh parent
    } catch (error) {
      console.error('Error saving month data:', error);
      alert(error.response?.data?.detail || 'Failed to save month data');
    } finally {
      setSaving(false);
    }
  };

  const handleResetDonation = () => {
    setDonationLbs('');
  };

  const handleResetCompost = () => {
    setCompostLbs('');
  };

  const formatNumber = (value) => {
    if (value === null || value === undefined) return '—';
    return typeof value === 'number' ? value.toLocaleString() : value;
  };

  const formatDecimal = (value, decimals = 2) => {
    if (value === null || value === undefined) return '—';
    return typeof value === 'number' ? value.toFixed(decimals) : value;
  };

  const getVarianceColor = (value) => {
    if (!value || value === 0) return '';
    return value < 0 ? 'positive' : 'negative';
  };

  if (loading) {
    return (
      <div className="modal-overlay" onClick={onClose}>
        <div className="modal-content month-detail-modal" onClick={(e) => e.stopPropagation()}>
          <div className="modal-loading">Loading...</div>
        </div>
      </div>
    );
  }

  const cafeCovers = metric?.cafe_covers || 0;
  const totalCovers = metric?.total_covers || 0;
  const totalDiversionLbs = metric?.total_diversion_lbs || 0;
  const totalDiversionGrams = metric?.total_diversion_grams || 0;
  const gramsPerCover = metric?.grams_per_cover;
  const variance = gramsPerCover !== null ? gramsPerCover - goalTarget : null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content month-detail-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <h2>{MONTHS[month - 1]} {year}</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        {/* Body */}
        <div className="modal-body">
          {/* Input Section */}
          <section className="input-section">
            <h3>Monthly Inputs</h3>
            <div className="input-grid">
              <div className="input-field">
                <label>F&B Covers</label>
                <input
                  type="number"
                  value={fbCovers}
                  onChange={(e) => setFbCovers(e.target.value)}
                  min="0"
                  placeholder="0"
                />
              </div>

              <div className="input-field">
                <label>FTE Count</label>
                <input
                  type="number"
                  value={fteCount}
                  onChange={(e) => setFteCount(e.target.value)}
                  min="0"
                  placeholder="0"
                />
              </div>

              <div className="input-field">
                <label>Temp Count</label>
                <input
                  type="number"
                  value={tempCount}
                  onChange={(e) => setTempCount(e.target.value)}
                  min="0"
                  placeholder="0"
                />
              </div>

              <div className="input-field">
                <label>Theoretic Capture %</label>
                <input
                  type="number"
                  value={capturePercent}
                  onChange={(e) => setCapturePercent(e.target.value)}
                  min="0"
                  max="100"
                  step="0.01"
                  placeholder="0.00"
                />
              </div>

              <div className="input-field calculated">
                <label>Cafeteria Covers</label>
                <div className="calculated-value">{formatNumber(cafeCovers)}</div>
                <div className="field-hint">Calculated: (FTE + Temp) × Capture %</div>
              </div>

              <div className="input-field">
                <label>Donation (lbs)</label>
                <div className="input-with-reset">
                  <input
                    type="number"
                    value={donationLbs}
                    onChange={(e) => setDonationLbs(e.target.value)}
                    min="0"
                    step="0.01"
                    placeholder="0.00"
                  />
                  {metric?.qr_donation_lbs > 0 && (
                    <button
                      type="button"
                      className="btn-reset"
                      onClick={handleResetDonation}
                      title="Reset to QR aggregate"
                    >
                      Reset
                    </button>
                  )}
                </div>
                {metric?.qr_donation_lbs > 0 && (
                  <div className="field-hint">
                    Auto: {formatDecimal(metric.qr_donation_lbs)} lbs from {metric.weigh_ins?.filter(w => w.category === 'donation').length || 0} entries
                  </div>
                )}
              </div>

              <div className="input-field">
                <label>Compost (lbs)</label>
                <div className="input-with-reset">
                  <input
                    type="number"
                    value={compostLbs}
                    onChange={(e) => setCompostLbs(e.target.value)}
                    min="0"
                    step="0.01"
                    placeholder="0.00"
                  />
                  {metric?.qr_compost_lbs > 0 && (
                    <button
                      type="button"
                      className="btn-reset"
                      onClick={handleResetCompost}
                      title="Reset to QR aggregate"
                    >
                      Reset
                    </button>
                  )}
                </div>
                {metric?.qr_compost_lbs > 0 && (
                  <div className="field-hint">
                    Auto: {formatDecimal(metric.qr_compost_lbs)} lbs from {metric.weigh_ins?.filter(w => w.category === 'compost').length || 0} entries
                  </div>
                )}
              </div>

              <div className="input-field full-width">
                <label>Notes</label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Optional notes for this month..."
                  rows={3}
                />
              </div>
            </div>
          </section>

          {/* QR Weigh-In Log */}
          {metric?.weigh_ins && metric.weigh_ins.length > 0 && (
            <section className="weighins-section">
              <h3>QR Weigh-In Log ({metric.weigh_ins.length})</h3>
              <div className="weighins-table-container">
                <table className="weighins-table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Category</th>
                      <th>Weight (lbs)</th>
                      <th>Token</th>
                      <th>Submitted</th>
                    </tr>
                  </thead>
                  <tbody>
                    {metric.weigh_ins.map((weighin) => (
                      <tr key={weighin.id}>
                        <td>{new Date(weighin.recorded_date).toLocaleDateString()}</td>
                        <td>
                          <span className={`category-badge ${weighin.category}`}>
                            {weighin.category}
                          </span>
                        </td>
                        <td className="data-cell">{formatDecimal(weighin.weight_lbs)}</td>
                        <td className="token-label">{weighin.token_label}</td>
                        <td className="timestamp">
                          {new Date(weighin.submitted_at).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          {/* Calculated Summary */}
          <section className="summary-section">
            <h3>Calculated Summary</h3>
            <div className="summary-grid">
              <div className="summary-item">
                <div className="summary-label">Total Covers</div>
                <div className="summary-value">{formatNumber(totalCovers)}</div>
              </div>

              <div className="summary-item">
                <div className="summary-label">Total Diversion</div>
                <div className="summary-value">
                  {formatDecimal(totalDiversionLbs)} lbs
                  <span className="summary-secondary">
                    ({formatNumber(Math.round(totalDiversionGrams))} g)
                  </span>
                </div>
              </div>

              <div className="summary-item primary">
                <div className="summary-label">Grams per Cover</div>
                <div className="summary-value large">
                  {formatDecimal(gramsPerCover)}
                </div>
              </div>

              <div className={`summary-item ${getVarianceColor(variance)}`}>
                <div className="summary-label">vs Goal</div>
                <div className="summary-value">
                  {variance !== null
                    ? `${variance > 0 ? '+' : ''}${formatDecimal(variance)}`
                    : '—'
                  }
                </div>
              </div>
            </div>
          </section>
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>
            Cancel
          </button>
          <button
            className="btn-primary"
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default MonthDetailModal;
