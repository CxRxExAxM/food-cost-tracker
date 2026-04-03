/**
 * Settings Tab Component (Placeholder)
 *
 * Module configuration:
 * - EHC Outlets management
 * - Audit cycle settings
 * - Responsibility codes
 * - NC level definitions
 *
 * TODO: Full implementation in Phase 7
 */

export default function Settings({ activeCycle }) {
  return (
    <div className="settings-view">
      <div className="placeholder-content">
        <h2>EHC Settings</h2>
        <p className="placeholder-description">
          Module configuration coming soon.
        </p>
        <ul className="placeholder-features">
          <li>Manage EHC outlets (kitchen areas, restaurants)</li>
          <li>Configure leader contacts for email distribution</li>
          <li>Audit cycle management</li>
          <li>Responsibility codes reference</li>
        </ul>
        <p className="placeholder-note">
          Cycle management is currently in the header dropdown.
        </p>
      </div>
    </div>
  );
}
