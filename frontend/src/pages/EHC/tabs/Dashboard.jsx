/**
 * Dashboard Tab Component
 *
 * Overview stats: progress rings, section progress, NC level breakdown.
 * All data comes from parent via props.
 */

import {
  ProgressRing,
  SectionProgress,
  NCBadge,
} from './shared';

export default function Dashboard({ dashboard, submissionStats }) {
  if (!dashboard) {
    return (
      <div className="dashboard-view">
        <div className="loading-state">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="dashboard-view">
      {/* Top Stats Row - Three Progress Rings */}
      <div className="stats-row stats-row-progress">
        <div className="stat-card progress-card progress-card-split">
          <ProgressRing
            percentage={dashboard.overall_progress?.prework?.completion_pct || 0}
            size={90}
            strokeWidth={6}
          />
          <div className="progress-details">
            <div className="stat-label">Pre-Work Ready</div>
            <div className="stat-breakdown">
              <span>{dashboard.overall_progress?.prework?.completed || 0}</span>
              <span className="stat-sep">/</span>
              <span>{dashboard.overall_progress?.prework?.total || 0} records</span>
            </div>
          </div>
        </div>

        <div className="stat-card progress-card progress-card-split">
          <ProgressRing
            percentage={dashboard.overall_progress?.internal_walk?.completion_pct || 0}
            size={90}
            strokeWidth={6}
          />
          <div className="progress-details">
            <div className="stat-label">Internal Walk</div>
            <div className="stat-breakdown">
              <span>{dashboard.overall_progress?.internal_walk?.completed || 0}</span>
              <span className="stat-sep">/</span>
              <span>{dashboard.overall_progress?.internal_walk?.total || 0} checked</span>
            </div>
          </div>
        </div>

        <div className="stat-card progress-card progress-card-split">
          <ProgressRing
            percentage={dashboard.overall_progress?.audit_walk?.completion_pct || 0}
            size={90}
            strokeWidth={6}
          />
          <div className="progress-details">
            <div className="stat-label">Audit Walk</div>
            <div className="stat-breakdown">
              <span>{dashboard.overall_progress?.audit_walk?.completed || 0}</span>
              <span className="stat-sep">/</span>
              <span>{dashboard.overall_progress?.audit_walk?.total || 0} verified</span>
            </div>
          </div>
        </div>

        <div className="stat-card stat-card-compact">
          <div className="stat-value stat-green">{submissionStats.approved}</div>
          <div className="stat-label">Approved</div>
        </div>

        <div className="stat-card stat-card-compact">
          <div className="stat-value stat-red">{submissionStats.pastDue}</div>
          <div className="stat-label">Past Due</div>
        </div>

        <div className="stat-card stat-card-compact">
          <div className="stat-value stat-yellow">{submissionStats.due}</div>
          <div className="stat-label">Due Now</div>
        </div>

        <div className="stat-card stat-card-compact">
          <div className="stat-value">{submissionStats.pending}</div>
          <div className="stat-label">Pending</div>
        </div>
      </div>

      {/* Progress Legend */}
      <div className="progress-legend">
        <span className="legend-item">
          <span className="legend-color legend-prework"></span>
          Pre-Work
        </span>
        <span className="legend-item">
          <span className="legend-color legend-internal"></span>
          Internal Walk
        </span>
        <span className="legend-item">
          <span className="legend-color legend-audit"></span>
          Audit Walk
        </span>
      </div>

      {/* Sections Progress */}
      <div className="sections-card">
        <h3>Section Progress</h3>
        <div className="sections-grid">
          {dashboard.sections?.map(section => (
            <SectionProgress key={section.id} section={section} />
          ))}
        </div>
      </div>

      {/* NC Level Breakdown */}
      <div className="nc-breakdown-card">
        <h3>Non-Conformance Level Breakdown</h3>
        <div className="nc-grid">
          {dashboard.nc_breakdown?.map(nc => (
            <div key={nc.nc_level} className="nc-item">
              <NCBadge level={nc.nc_level} />
              <div className="nc-progress">
                <div className="nc-progress-bar stacked-bar">
                  <div
                    className="stacked-segment segment-prework"
                    style={{ width: `${nc.prework_pct || 0}%` }}
                    title={`Pre-Work: ${nc.prework_pct || 0}%`}
                  />
                  <div
                    className="stacked-segment segment-internal"
                    style={{ width: `${nc.internal_pct || 0}%` }}
                    title={`Internal Walk: ${nc.internal_pct || 0}%`}
                  />
                  <div
                    className="stacked-segment segment-audit"
                    style={{ width: `${nc.audit_pct || 0}%` }}
                    title={`Audit Walk: ${nc.audit_pct || 0}%`}
                  />
                </div>
                <span className="nc-progress-text">
                  {nc.completed} / {nc.total} ({nc.completion_pct}%)
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
