import { useState, useMemo } from 'react';
import SignaturePad from './SignaturePad';
import { RECORD_35 } from './templates/record_35';
import { Check } from 'lucide-react';
import './TeamRosterForm.css';

/**
 * Team Roster Form (Record 35)
 *
 * Features:
 * - Displays team member table from config
 * - Each row has sign button that expands signature pad inline
 * - Shows completion status (signed/awaiting)
 */
export default function TeamRosterForm({
  config,
  existingResponses = [],
  onSubmit,
  submitting = false
}) {
  const [activeSigningIndex, setActiveSigningIndex] = useState(null);
  const [signature, setSignature] = useState(null);

  const teamMembers = config?.team_members || [];
  const propertyName = config?.property_name || 'Property';
  const cycleYear = config?.cycle_year || new Date().getFullYear();

  // Map existing responses to team member indices
  const signedIndices = useMemo(() => {
    const map = new Map();
    existingResponses.forEach(resp => {
      if (resp.response_data?.team_member_index !== undefined) {
        map.set(resp.response_data.team_member_index, resp);
      }
    });
    return map;
  }, [existingResponses]);

  const handleSignClick = (index) => {
    setActiveSigningIndex(activeSigningIndex === index ? null : index);
    setSignature(null);
  };

  const handleSubmit = (memberIndex) => {
    if (!signature || submitting) return;

    const member = teamMembers[memberIndex];
    onSubmit({
      respondent_name: member.name,
      respondent_role: member.position,
      respondent_dept: member.department,
      response_data: {
        team_member_index: memberIndex,
        date_approved: member.date_approved
      },
      signature_data: signature
    });

    setActiveSigningIndex(null);
    setSignature(null);
  };

  const allSigned = teamMembers.length > 0 &&
    teamMembers.every((_, idx) => signedIndices.has(idx));

  return (
    <div className="team-roster-form">
      {/* Header */}
      <div className="form-header">
        <h1 className="form-title">{RECORD_35.title}</h1>
        <div className="form-meta">
          <span>{propertyName}</span>
          <span className="meta-divider">•</span>
          <span>EHC {cycleYear}</span>
        </div>
        <div className="form-version">{RECORD_35.version}</div>
      </div>

      {/* Intro */}
      <div className="roster-intro">
        {RECORD_35.intro.map((para, idx) => (
          <p key={idx}>{para}</p>
        ))}
      </div>

      {/* Completion Banner */}
      {allSigned && (
        <div className="completion-banner">
          <Check size={20} />
          <span>All team members have signed</span>
        </div>
      )}

      {/* Progress */}
      <div className="roster-progress">
        <span className="progress-count">
          {signedIndices.size} of {teamMembers.length} signed
        </span>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ width: `${(signedIndices.size / teamMembers.length) * 100}%` }}
          />
        </div>
      </div>

      {/* Team Table */}
      <div className="roster-table-container">
        <table className="roster-table">
          <thead>
            <tr>
              <th>{RECORD_35.tableHeaders.dateApproved}</th>
              <th>{RECORD_35.tableHeaders.name}</th>
              <th>{RECORD_35.tableHeaders.position}</th>
              <th>{RECORD_35.tableHeaders.department}</th>
              <th>{RECORD_35.tableHeaders.signature}</th>
            </tr>
          </thead>
          <tbody>
            {teamMembers.map((member, idx) => {
              const existingResponse = signedIndices.get(idx);
              const isSigned = !!existingResponse;
              const isActive = activeSigningIndex === idx;

              return (
                <tr key={idx} className={isActive ? 'active-row' : ''}>
                  <td className="date-cell">
                    {member.date_approved
                      ? new Date(member.date_approved).toLocaleDateString()
                      : '—'}
                  </td>
                  <td className="name-cell">{member.name}</td>
                  <td>{member.position}</td>
                  <td>{member.department}</td>
                  <td className="signature-cell">
                    {isSigned ? (
                      <div className="signed-indicator">
                        <Check size={16} />
                        <span>Signed</span>
                      </div>
                    ) : (
                      <button
                        type="button"
                        className={`btn-sign ${isActive ? 'active' : ''}`}
                        onClick={() => handleSignClick(idx)}
                      >
                        {isActive ? 'Cancel' : 'Sign'}
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Inline Signature Area */}
      {activeSigningIndex !== null && (
        <div className="inline-signature-area">
          <div className="signing-for">
            Signing as: <strong>{teamMembers[activeSigningIndex]?.name}</strong>
          </div>

          <SignaturePad
            onSignatureChange={setSignature}
          />

          <button
            type="button"
            className="btn-submit-signature"
            disabled={!signature || submitting}
            onClick={() => handleSubmit(activeSigningIndex)}
          >
            {submitting ? 'Submitting...' : 'Submit Signature'}
          </button>
        </div>
      )}

      {/* Empty state */}
      {teamMembers.length === 0 && (
        <div className="empty-state">
          No team members configured for this form.
        </div>
      )}
    </div>
  );
}
