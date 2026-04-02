import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import axios from '../../../lib/axios';
import StaffDeclarationForm from './StaffDeclarationForm';
import TeamRosterForm from './TeamRosterForm';
import { CheckCircle, AlertTriangle, Clock } from 'lucide-react';
import './FormPage.css';

/**
 * Public Form Page
 *
 * Route: /form/:token
 * No authentication required - token provides access control.
 *
 * Fetches form data and renders the appropriate form type.
 */
export default function FormPage() {
  const { token } = useParams();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [formData, setFormData] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [submittedName, setSubmittedName] = useState('');

  // Fetch form data
  useEffect(() => {
    const fetchForm = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await axios.get(`/api/ehc/forms/${token}`);
        setFormData(response.data);
      } catch (err) {
        console.error('Error fetching form:', err);

        if (err.response?.status === 404) {
          setError({ type: 'not_found', message: 'Form not found' });
        } else if (err.response?.status === 410) {
          const detail = err.response?.data?.detail || 'Form expired';
          setError({ type: 'expired', message: detail });
        } else {
          setError({
            type: 'error',
            message: err.response?.data?.detail || 'Failed to load form'
          });
        }
      } finally {
        setLoading(false);
      }
    };

    if (token) {
      fetchForm();
    }
  }, [token]);

  // Handle form submission
  const handleSubmit = async (data) => {
    try {
      setSubmitting(true);

      const response = await axios.post(`/api/ehc/forms/${token}/respond`, data);

      setSubmittedName(data.respondent_name);
      setSubmitted(true);

      // Refresh form data to show updated response count
      const refreshed = await axios.get(`/api/ehc/forms/${token}`);
      setFormData(refreshed.data);
    } catch (err) {
      console.error('Error submitting form:', err);

      if (err.response?.status === 409) {
        // Duplicate - ask to force
        const detail = err.response?.data?.detail;
        const confirm = window.confirm(
          `${detail?.message || 'A response already exists'}. Do you want to replace it?`
        );

        if (confirm) {
          // Retry with force=true
          try {
            await axios.post(`/api/ehc/forms/${token}/respond?force=true`, data);
            setSubmittedName(data.respondent_name);
            setSubmitted(true);

            const refreshed = await axios.get(`/api/ehc/forms/${token}`);
            setFormData(refreshed.data);
          } catch (retryErr) {
            alert(retryErr.response?.data?.detail || 'Failed to submit');
          }
        }
      } else {
        alert(err.response?.data?.detail || 'Failed to submit. Please try again.');
      }
    } finally {
      setSubmitting(false);
    }
  };

  // Loading state
  if (loading) {
    return (
      <div className="form-page">
        <div className="form-page-container">
          <div className="loading-state">
            <div className="loading-spinner" />
            <span>Loading form...</span>
          </div>
        </div>
      </div>
    );
  }

  // Error states
  if (error) {
    return (
      <div className="form-page">
        <div className="form-page-container">
          <div className={`error-state ${error.type}`}>
            {error.type === 'expired' ? (
              <Clock size={48} />
            ) : (
              <AlertTriangle size={48} />
            )}
            <h2>
              {error.type === 'not_found' && 'Form Not Found'}
              {error.type === 'expired' && 'Form Expired'}
              {error.type === 'error' && 'Error'}
            </h2>
            <p>{error.message}</p>
          </div>
        </div>
      </div>
    );
  }

  // Success state after submission
  if (submitted) {
    return (
      <div className="form-page">
        <div className="form-page-container">
          <div className="success-state">
            <CheckCircle size={64} />
            <h2>Thank You!</h2>
            <p>
              Your response has been recorded, <strong>{submittedName}</strong>.
            </p>
            <div className="success-meta">
              <span>{formData?.title}</span>
              <span className="meta-divider">•</span>
              <span>{new Date().toLocaleDateString()}</span>
            </div>
            <button
              className="btn-another"
              onClick={() => setSubmitted(false)}
            >
              Submit Another Response
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Render appropriate form type
  const renderForm = () => {
    const { form_type, config, responses } = formData;

    switch (form_type) {
      case 'staff_declaration':
        return (
          <StaffDeclarationForm
            config={config}
            existingResponses={responses}
            onSubmit={handleSubmit}
            submitting={submitting}
          />
        );

      case 'team_roster':
        return (
          <TeamRosterForm
            config={config}
            existingResponses={responses}
            onSubmit={handleSubmit}
            submitting={submitting}
          />
        );

      default:
        return (
          <div className="unsupported-form">
            <AlertTriangle size={32} />
            <p>This form type is not yet supported.</p>
          </div>
        );
    }
  };

  return (
    <div className="form-page">
      <div className="form-page-container">
        {/* Progress indicator */}
        {formData?.expected_responses && (
          <div className="form-progress-bar">
            <div className="progress-info">
              <span>
                {formData.total_responses} of {formData.expected_responses} responses
              </span>
            </div>
            <div className="progress-track">
              <div
                className="progress-fill"
                style={{
                  width: `${Math.min(
                    (formData.total_responses / formData.expected_responses) * 100,
                    100
                  )}%`
                }}
              />
            </div>
          </div>
        )}

        {renderForm()}

        {/* Footer */}
        <div className="form-footer">
          <span>Powered by RestauranTek</span>
        </div>
      </div>
    </div>
  );
}
