/**
 * Forms Tab Component (Placeholder)
 *
 * Admin workbench for digital form management:
 * - Create form links
 * - Track responses
 * - Download PDFs
 * - Batch operations
 *
 * TODO: Full implementation in Phase 6
 */

export default function Forms({ activeCycle }) {
  return (
    <div className="forms-view">
      <div className="placeholder-content">
        <h2>Forms Management</h2>
        <p className="placeholder-description">
          Digital form administration coming soon.
        </p>
        <ul className="placeholder-features">
          <li>Create and manage form links (QR codes)</li>
          <li>Track response collection progress</li>
          <li>Download completed signature PDFs</li>
          <li>Batch generate forms for all outlets</li>
        </ul>
        <p className="placeholder-note">
          For now, use the Records tab to access form links via the 🔗 icon.
        </p>
      </div>
    </div>
  );
}
