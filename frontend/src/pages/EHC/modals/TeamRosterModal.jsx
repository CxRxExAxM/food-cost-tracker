/**
 * Team Roster Form Creation Modal
 *
 * For Record 35 style forms:
 * - Admin pre-configures team members (name, position, department)
 * - Each team member finds their row and signs
 * - Small team (5-10 people)
 */

import { useState, useEffect } from 'react';
import { API_BASE, fetchWithAuth } from '../tabs/shared';

const EMPTY_MEMBER = { name: '', position: '', department: '', date_approved: '' };

export default function TeamRosterModal({
  isOpen,
  onClose,
  activeCycle,
  onFormCreated,
  toast
}) {
  const [title, setTitle] = useState('');
  const [teamMembers, setTeamMembers] = useState([{ ...EMPTY_MEMBER }]);
  const [creating, setCreating] = useState(false);

  // Reset state when modal opens
  useEffect(() => {
    if (isOpen) {
      setTitle(`Food Safety Team Record - EHC ${activeCycle?.year || new Date().getFullYear()}`);
      setTeamMembers([{ ...EMPTY_MEMBER }]);
    }
  }, [isOpen, activeCycle?.year]);

  function addTeamMember() {
    setTeamMembers([...teamMembers, { ...EMPTY_MEMBER }]);
  }

  function removeTeamMember(index) {
    if (teamMembers.length <= 1) return;
    setTeamMembers(teamMembers.filter((_, i) => i !== index));
  }

  function updateTeamMember(index, field, value) {
    setTeamMembers(teamMembers.map((member, i) =>
      i === index ? { ...member, [field]: value } : member
    ));
  }

  async function handleCreate() {
    // Validate at least one team member with a name
    const validMembers = teamMembers.filter(m => m.name.trim());
    if (validMembers.length === 0) {
      toast?.error?.('Add at least one team member');
      return;
    }

    try {
      setCreating(true);

      const config = {
        team_members: validMembers,
        property_name: 'Fairmont Scottsdale Princess' // TODO: Get from org settings
      };

      // First, get the actual record ID for record_number = '35'
      const recordsData = await fetchWithAuth(`${API_BASE}/cycles/${activeCycle.id}/records`);
      const record35 = recordsData.data.find(r => r.record_number === '35');

      if (!record35) {
        throw new Error('Record 35 not found');
      }

      const payload = {
        form_type: 'team_roster',
        record_id: record35.id,
        title: title || `Food Safety Team Record - EHC ${activeCycle.year}`,
        config,
        expected_responses: validMembers.length
      };

      const data = await fetchWithAuth(`${API_BASE}/cycles/${activeCycle.id}/form-links`, {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      toast?.success?.('Team Roster form created');
      onFormCreated?.(data);
      onClose();
    } catch (error) {
      toast?.error?.(error.message || 'Failed to create form link');
    } finally {
      setCreating(false);
    }
  }

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content form-create-modal wide" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Create Team Roster Form</h3>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
          <div className="form-type-info">
            <span className="form-type-icon">👥</span>
            <div>
              <strong>Record 35: Food Safety Team Record</strong>
              <p>
                Configure your food safety team members below. Each person will find
                their name on the form and sign to confirm their role on the team.
              </p>
            </div>
          </div>

          <div className="form-field">
            <label>Form Title</label>
            <input
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder={`Food Safety Team Record - EHC ${activeCycle?.year}`}
            />
          </div>

          <div className="form-field">
            <label>Team Members</label>
            <div className="team-members-editor">
              <div className="team-header">
                <span>Name</span>
                <span>Position</span>
                <span>Department</span>
                <span>Date Approved</span>
                <span></span>
              </div>
              {teamMembers.map((member, index) => (
                <div key={index} className="team-member-row">
                  <input
                    type="text"
                    value={member.name}
                    onChange={e => updateTeamMember(index, 'name', e.target.value)}
                    placeholder="Full Name"
                  />
                  <input
                    type="text"
                    value={member.position}
                    onChange={e => updateTeamMember(index, 'position', e.target.value)}
                    placeholder="Position"
                  />
                  <input
                    type="text"
                    value={member.department}
                    onChange={e => updateTeamMember(index, 'department', e.target.value)}
                    placeholder="Department"
                  />
                  <input
                    type="date"
                    value={member.date_approved}
                    onChange={e => updateTeamMember(index, 'date_approved', e.target.value)}
                  />
                  <button
                    className="btn-icon danger"
                    onClick={() => removeTeamMember(index)}
                    disabled={teamMembers.length <= 1}
                    title="Remove"
                  >
                    ✕
                  </button>
                </div>
              ))}
              <button className="btn-add-member" onClick={addTeamMember}>
                + Add Team Member
              </button>
            </div>
          </div>

          <div className="modal-actions">
            <button className="btn-ghost" onClick={onClose}>Cancel</button>
            <button
              className="btn-primary"
              onClick={handleCreate}
              disabled={creating || !teamMembers.some(m => m.name.trim())}
            >
              {creating ? 'Creating...' : 'Create Form Link'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
