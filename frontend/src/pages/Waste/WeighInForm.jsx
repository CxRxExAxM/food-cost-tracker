import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from '../../lib/axios';
import './WeighInForm.css';

function WeighInForm() {
  const { token } = useParams();
  const navigate = useNavigate();

  const [tokenInfo, setTokenInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  // Form fields
  const [recordedDate, setRecordedDate] = useState(new Date().toISOString().split('T')[0]);
  const [category, setCategory] = useState('compost');
  const [weightLbs, setWeightLbs] = useState('');
  const [submittedByName, setSubmittedByName] = useState('');

  useEffect(() => {
    fetchTokenInfo();
  }, [token]);

  const fetchTokenInfo = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`/waste/weigh-in/${token}/info`);
      setTokenInfo(response.data);
    } catch (error) {
      console.error('Error fetching token info:', error);
      if (error.response?.status === 404) {
        alert('Invalid QR code');
      } else if (error.response?.status === 403) {
        alert('This QR code is no longer active');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    // Validate
    const weight = parseFloat(weightLbs);
    if (isNaN(weight) || weight <= 0) {
      alert('Please enter a valid weight greater than 0');
      return;
    }

    setSubmitting(true);
    try {
      await axios.post(`/waste/weigh-in/${token}`, {
        recorded_date: recordedDate,
        category,
        weight_lbs: weight,
        submitted_by_name: submittedByName || null
      });

      setSubmitted(true);

      // Reset form after 3 seconds
      setTimeout(() => {
        setWeightLbs('');
        setSubmittedByName('');
        setRecordedDate(new Date().toISOString().split('T')[0]);
        setSubmitted(false);
      }, 3000);
    } catch (error) {
      console.error('Error submitting weigh-in:', error);
      alert(error.response?.data?.detail || 'Failed to submit weigh-in');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="weighin-page">
        <div className="weighin-container">
          <div className="loading">Loading...</div>
        </div>
      </div>
    );
  }

  if (!tokenInfo) {
    return (
      <div className="weighin-page">
        <div className="weighin-container">
          <div className="error-message">
            <h2>Invalid QR Code</h2>
            <p>This QR code is not recognized. Please check with your manager.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="weighin-page">
      <div className="weighin-container">
        <header className="weighin-header">
          <h1>🌱 Waste Weigh-In</h1>
          <p className="station-label">{tokenInfo.label}</p>
        </header>

        {submitted ? (
          <div className="success-message">
            <div className="success-icon">✓</div>
            <h2>Weigh-In Submitted!</h2>
            <p>Thank you for tracking our waste diversion</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="weighin-form">
            <div className="form-field">
              <label>Date</label>
              <input
                type="date"
                value={recordedDate}
                onChange={(e) => setRecordedDate(e.target.value)}
                required
                max={new Date().toISOString().split('T')[0]}
              />
            </div>

            <div className="form-field">
              <label>Category</label>
              <div className="radio-group">
                <label className="radio-option">
                  <input
                    type="radio"
                    value="compost"
                    checked={category === 'compost'}
                    onChange={(e) => setCategory(e.target.value)}
                  />
                  <span className="radio-label">
                    <span className="radio-icon">🗑️</span>
                    Compost
                  </span>
                </label>
                <label className="radio-option">
                  <input
                    type="radio"
                    value="donation"
                    checked={category === 'donation'}
                    onChange={(e) => setCategory(e.target.value)}
                  />
                  <span className="radio-label">
                    <span className="radio-icon">🎁</span>
                    Donation
                  </span>
                </label>
              </div>
            </div>

            <div className="form-field">
              <label>Weight (pounds)</label>
              <input
                type="number"
                value={weightLbs}
                onChange={(e) => setWeightLbs(e.target.value)}
                min="0.01"
                step="0.01"
                placeholder="0.00"
                required
                autoFocus
              />
            </div>

            <div className="form-field">
              <label>Your Name (optional)</label>
              <input
                type="text"
                value={submittedByName}
                onChange={(e) => setSubmittedByName(e.target.value)}
                placeholder="Enter your name"
                maxLength={100}
              />
            </div>

            <button
              type="submit"
              className="btn-submit"
              disabled={submitting}
            >
              {submitting ? 'Submitting...' : 'Submit Weigh-In'}
            </button>
          </form>
        )}

        <footer className="weighin-footer">
          <p>Part of our commitment to sustainability 🌍</p>
        </footer>
      </div>
    </div>
  );
}

export default WeighInForm;
