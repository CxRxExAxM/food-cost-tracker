import { useState, useMemo } from 'react';
import { useParams } from 'react-router-dom';
import SignaturePad from './SignaturePad';
import { Check, X, AlertTriangle, ChevronDown, ChevronUp, FileText, ExternalLink } from 'lucide-react';
import './ChecklistForm.css';

/**
 * Checklist Form (Y/N Questions with Corrective Actions)
 *
 * Mobile-first design for kitchen walkthrough audits.
 * Features:
 * - 58 Y/N questions in scrollable list
 * - "N" answers expand corrective action fields inline
 * - Progress indicator (32/58 answered)
 * - Scroll-to-sign gate at bottom
 * - Single submission per form (one outlet's checklist)
 */
export default function ChecklistForm({
  config,
  title,
  existingResponses = [],
  onSubmit,
  submitting = false
}) {
  const { token } = useParams();

  // Answers state: { "1": { answer: "Y" }, "2": { answer: "N", action: "...", when_by: "...", who_by: "..." } }
  const [answers, setAnswers] = useState({});
  const [signature, setSignature] = useState(null);
  const [respondentName, setRespondentName] = useState('');
  const [expandedQuestion, setExpandedQuestion] = useState(null);
  const [showSignature, setShowSignature] = useState(false);

  const items = config?.items || [];
  const introText = config?.intro_text || '';
  const outletName = config?.outlet_name || '';
  const periodLabel = config?.period_label || '';
  const propertyName = config?.property_name || 'Property';
  const requireCorrectiveActions = config?.corrective_actions !== false;
  const documentPath = config?.document_path;

  // Check if form already has a response (checklist forms are one-per-outlet)
  const alreadySubmitted = existingResponses.length > 0;
  const existingResponse = existingResponses[0];

  // Count answered questions
  const answeredCount = Object.keys(answers).filter(k => answers[k]?.answer).length;
  const totalQuestions = items.length;
  const progress = totalQuestions > 0 ? (answeredCount / totalQuestions) * 100 : 0;

  // Count N answers that need corrective action
  const nAnswersNeedingAction = useMemo(() => {
    if (!requireCorrectiveActions) return [];
    return Object.entries(answers)
      .filter(([_, data]) => data.answer === 'N' && !data.action?.trim())
      .map(([num]) => num);
  }, [answers, requireCorrectiveActions]);

  // Check if ready to sign
  const allAnswered = answeredCount === totalQuestions;
  const allActionsComplete = nAnswersNeedingAction.length === 0;
  const canSign = allAnswered && allActionsComplete;

  // Handle answer selection
  const handleAnswer = (questionNum, answer) => {
    setAnswers(prev => ({
      ...prev,
      [questionNum]: {
        ...prev[questionNum],
        answer
      }
    }));

    // If answering N and corrective actions required, expand the question
    if (answer === 'N' && requireCorrectiveActions) {
      setExpandedQuestion(questionNum);
    } else if (answer === 'Y' && expandedQuestion === questionNum) {
      setExpandedQuestion(null);
    }
  };

  // Handle corrective action field changes
  const handleActionChange = (questionNum, field, value) => {
    setAnswers(prev => ({
      ...prev,
      [questionNum]: {
        ...prev[questionNum],
        [field]: value
      }
    }));
  };

  // Toggle question expansion (for viewing/editing corrective action)
  const toggleExpand = (questionNum) => {
    if (expandedQuestion === questionNum) {
      setExpandedQuestion(null);
    } else {
      setExpandedQuestion(questionNum);
    }
  };

  // Handle form submission
  const handleSubmit = () => {
    if (!signature || !respondentName.trim() || submitting) return;

    onSubmit({
      respondent_name: respondentName.trim(),
      response_data: {
        answers,
        completed_at: new Date().toISOString(),
        outlet_name: outletName
      },
      signature_data: signature
    });
  };

  // If already submitted, show read-only view
  if (alreadySubmitted && existingResponse) {
    const submittedAnswers = existingResponse.response_data?.answers || {};
    const yesCount = Object.values(submittedAnswers).filter(a => a.answer === 'Y').length;
    const noCount = Object.values(submittedAnswers).filter(a => a.answer === 'N').length;

    return (
      <div className="checklist-form completed">
        {/* Header */}
        <div className="form-header">
          <h1 className="form-title">{title || 'Kitchen Audit Checklist'}</h1>
          <div className="form-meta">
            {outletName && <span className="outlet-name">{outletName}</span>}
            {periodLabel && <span className="period-label">{periodLabel}</span>}
          </div>
        </div>

        {/* Completion Banner */}
        <div className="completion-banner">
          <Check size={24} />
          <div className="completion-info">
            <strong>Checklist Completed</strong>
            <span>Submitted by {existingResponse.respondent_name}</span>
          </div>
        </div>

        {/* Summary */}
        <div className="results-summary">
          <div className="result-stat yes">
            <span className="stat-value">{yesCount}</span>
            <span className="stat-label">Yes</span>
          </div>
          <div className="result-stat no">
            <span className="stat-value">{noCount}</span>
            <span className="stat-label">No</span>
          </div>
          <div className="result-stat total">
            <span className="stat-value">{items.length}</span>
            <span className="stat-label">Total</span>
          </div>
        </div>

        {/* Show N answers with corrective actions */}
        {noCount > 0 && (
          <div className="corrective-actions-summary">
            <h3>Items Requiring Action ({noCount})</h3>
            {items.filter(item => submittedAnswers[item.number]?.answer === 'N').map(item => {
              const answer = submittedAnswers[item.number];
              return (
                <div key={item.number} className="action-item">
                  <div className="action-question">
                    <span className="q-number">{item.number}.</span>
                    <span className="q-text">{item.question}</span>
                  </div>
                  {answer.action && (
                    <div className="action-details">
                      <div className="action-row">
                        <span className="label">Action:</span>
                        <span className="value">{answer.action}</span>
                      </div>
                      {answer.when_by && (
                        <div className="action-row">
                          <span className="label">When:</span>
                          <span className="value">{answer.when_by}</span>
                        </div>
                      )}
                      {answer.who_by && (
                        <div className="action-row">
                          <span className="label">Who:</span>
                          <span className="value">{answer.who_by}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="checklist-form">
      {/* Header */}
      <div className="form-header">
        <h1 className="form-title">{title || 'Kitchen Audit Checklist'}</h1>
        <div className="form-meta">
          {outletName && <span className="outlet-name">{outletName}</span>}
          {periodLabel && <span className="period-label">{periodLabel}</span>}
        </div>
      </div>

      {/* Intro */}
      {introText && (
        <div className="form-intro">
          <p>{introText}</p>
        </div>
      )}

      {/* PDF Document */}
      {documentPath && (
        <a
          href={`/api/ehc/forms/${token}/document`}
          target="_blank"
          rel="noopener noreferrer"
          className="view-document-btn"
        >
          <FileText size={18} />
          <span>View Reference Document</span>
          <ExternalLink size={16} />
        </a>
      )}

      {/* Progress Bar */}
      <div className="checklist-progress">
        <div className="progress-info">
          <span className="progress-count">
            <strong>{answeredCount}</strong> of <strong>{totalQuestions}</strong> answered
          </span>
          {nAnswersNeedingAction.length > 0 && (
            <span className="actions-needed">
              <AlertTriangle size={14} />
              {nAnswersNeedingAction.length} need action
            </span>
          )}
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Questions List */}
      <div className="questions-list">
        {items.map((item, idx) => {
          const questionNum = String(item.number);
          const answer = answers[questionNum]?.answer;
          const isExpanded = expandedQuestion === questionNum;
          const hasAnswer = !!answer;
          const needsAction = answer === 'N' && requireCorrectiveActions && !answers[questionNum]?.action?.trim();

          return (
            <div
              key={item.number}
              className={`question-item ${hasAnswer ? 'answered' : ''} ${answer === 'N' ? 'no-answer' : ''} ${needsAction ? 'needs-action' : ''}`}
            >
              <div className="question-row">
                <span className="question-number">{item.number}</span>
                <p className="question-text">{item.question}</p>
                <div className="answer-buttons">
                  <button
                    type="button"
                    className={`btn-answer yes ${answer === 'Y' ? 'selected' : ''}`}
                    onClick={() => handleAnswer(questionNum, 'Y')}
                  >
                    <Check size={18} />
                    <span>Y</span>
                  </button>
                  <button
                    type="button"
                    className={`btn-answer no ${answer === 'N' ? 'selected' : ''}`}
                    onClick={() => handleAnswer(questionNum, 'N')}
                  >
                    <X size={18} />
                    <span>N</span>
                  </button>
                </div>
              </div>

              {/* Corrective Action Section (for N answers) */}
              {answer === 'N' && requireCorrectiveActions && (
                <div className="corrective-action-section">
                  <button
                    type="button"
                    className="expand-action-btn"
                    onClick={() => toggleExpand(questionNum)}
                  >
                    <AlertTriangle size={14} />
                    <span>Corrective Action Required</span>
                    {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>

                  {isExpanded && (
                    <div className="action-fields">
                      <div className="action-field">
                        <label>Action to be taken *</label>
                        <textarea
                          value={answers[questionNum]?.action || ''}
                          onChange={e => handleActionChange(questionNum, 'action', e.target.value)}
                          placeholder="Describe the corrective action..."
                          rows={2}
                        />
                      </div>
                      <div className="action-field-row">
                        <div className="action-field">
                          <label>When by</label>
                          <input
                            type="date"
                            value={answers[questionNum]?.when_by || ''}
                            onChange={e => handleActionChange(questionNum, 'when_by', e.target.value)}
                          />
                        </div>
                        <div className="action-field">
                          <label>Who by</label>
                          <input
                            type="text"
                            value={answers[questionNum]?.who_by || ''}
                            onChange={e => handleActionChange(questionNum, 'who_by', e.target.value)}
                            placeholder="Name/Role"
                          />
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Sign Section */}
      <div className="sign-section">
        {!canSign ? (
          <div className="sign-blocked">
            <AlertTriangle size={20} />
            <div className="blocked-info">
              {!allAnswered && (
                <p>Answer all {totalQuestions - answeredCount} remaining questions to sign</p>
              )}
              {allAnswered && !allActionsComplete && (
                <p>Complete corrective actions for {nAnswersNeedingAction.length} item(s)</p>
              )}
            </div>
          </div>
        ) : !showSignature ? (
          <button
            type="button"
            className="btn-ready-to-sign"
            onClick={() => setShowSignature(true)}
          >
            <Check size={20} />
            <span>All questions answered - Tap to sign</span>
          </button>
        ) : (
          <div className="signature-area">
            <h3>Sign to Complete</h3>

            <div className="name-field">
              <label>Your Name *</label>
              <input
                type="text"
                value={respondentName}
                onChange={e => setRespondentName(e.target.value)}
                placeholder="Enter your name"
              />
            </div>

            <div className="signature-pad-wrapper">
              <label>Signature *</label>
              <SignaturePad onSignatureChange={setSignature} />
            </div>

            <button
              type="button"
              className="btn-submit-checklist"
              disabled={!signature || !respondentName.trim() || submitting}
              onClick={handleSubmit}
            >
              {submitting ? 'Submitting...' : 'Submit Checklist'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
