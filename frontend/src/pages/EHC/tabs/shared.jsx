/**
 * Shared EHC Components
 *
 * Badge components, progress indicators, and utilities used across all EHC tabs.
 */

// API Configuration
export const API_BASE = '/api/ehc';

export function getAuthHeaders() {
  const token = localStorage.getItem('token');
  return {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  };
}

export async function fetchWithAuth(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...options.headers
    }
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }
  return response.json();
}

// Status badge component
export function StatusBadge({ status }) {
  const statusConfig = {
    not_started: { label: 'Not Started', class: 'badge-neutral' },
    in_progress: { label: 'In Progress', class: 'badge-yellow' },
    evidence_collected: { label: 'Evidence Collected', class: 'badge-blue' },
    verified: { label: 'Verified', class: 'badge-green' },
    flagged: { label: 'Flagged', class: 'badge-red' },
    pending: { label: 'Pending', class: 'badge-neutral' },
    submitted: { label: 'Submitted', class: 'badge-yellow' },
    approved: { label: 'Approved', class: 'badge-green' },
    not_applicable: { label: 'N/A', class: 'badge-neutral' },
  };

  const config = statusConfig[status] || { label: status, class: 'badge-neutral' };

  return <span className={`status-badge ${config.class}`}>{config.label}</span>;
}

// NC Level badge component
export function NCBadge({ level }) {
  const ncConfig = {
    1: { label: 'NC1', class: 'nc-critical', title: 'Critical - Food Safety Risk' },
    2: { label: 'NC2', class: 'nc-operational', title: 'Operational Compliance' },
    3: { label: 'NC3', class: 'nc-structural', title: 'Structural/Documentation' },
    4: { label: 'NC4', class: 'nc-admin', title: 'Administrative Records' },
  };

  const config = ncConfig[level] || { label: `NC${level}`, class: 'nc-admin' };

  return (
    <span className={`nc-badge ${config.class}`} title={config.title}>
      {config.label}
    </span>
  );
}

// Progress ring component
export function ProgressRing({ percentage, size = 120, strokeWidth = 8 }) {
  const radius = (size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (percentage / 100) * circumference;

  const getColor = (pct) => {
    if (pct >= 80) return 'var(--color-green)';
    if (pct >= 50) return 'var(--color-yellow)';
    return 'var(--color-red)';
  };

  return (
    <div className="progress-ring-container">
      <svg width={size} height={size} className="progress-ring">
        <circle
          className="progress-ring-bg"
          stroke="var(--border-subtle)"
          fill="transparent"
          strokeWidth={strokeWidth}
          r={radius}
          cx={size / 2}
          cy={size / 2}
        />
        <circle
          className="progress-ring-progress"
          stroke={getColor(percentage)}
          fill="transparent"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          r={radius}
          cx={size / 2}
          cy={size / 2}
          style={{ transform: 'rotate(-90deg)', transformOrigin: '50% 50%' }}
        />
      </svg>
      <div className="progress-ring-text">
        <span className="progress-ring-value">{Math.round(percentage)}%</span>
        <span className="progress-ring-label">Complete</span>
      </div>
    </div>
  );
}

// Section progress bar with stacked segments
export function SectionProgress({ section }) {
  const progress = section.progress || {};
  const preworkPct = progress.prework_pct || 0;
  const internalPct = progress.internal_pct || 0;
  const auditPct = progress.audit_pct || 0;
  const totalPct = progress.completion_pct || 0;

  return (
    <div className="section-progress">
      <div className="section-progress-header">
        <span className="section-number">{section.ref_number}</span>
        <span className="section-name">{section.name}</span>
        <span className="section-pct">{totalPct}%</span>
      </div>
      <div className="section-progress-bar stacked-bar">
        <div
          className="stacked-segment segment-prework"
          style={{ width: `${preworkPct}%` }}
          title={`Pre-Work: ${preworkPct}%`}
        />
        <div
          className="stacked-segment segment-internal"
          style={{ width: `${internalPct}%` }}
          title={`Internal Walk: ${internalPct}%`}
        />
        <div
          className="stacked-segment segment-audit"
          style={{ width: `${auditPct}%` }}
          title={`Audit Walk: ${auditPct}%`}
        />
      </div>
      <div className="section-progress-stats">
        <span>{progress.completed_points || 0} / {progress.total_points || 0} points</span>
      </div>
    </div>
  );
}

// Location badge component
export function LocationBadge({ type }) {
  const isOutlet = type === 'outlet_book';
  return (
    <span className={`location-badge ${isOutlet ? 'location-outlet' : 'location-office'}`}>
      {isOutlet ? 'Outlet Book' : 'Office Book'}
    </span>
  );
}

// Responsibility badge component
export function ResponsibilityBadge({ code }) {
  const codeConfig = {
    MM: { label: 'MM', title: 'Mike / Audit Prep Manager' },
    CF: { label: 'CF', title: 'Chef (Executive Chef)' },
    CM: { label: 'CM', title: 'Commissary / Purchasing' },
    AM: { label: 'AM', title: 'Area Manager / Assistant Manager' },
    ENG: { label: 'ENG', title: 'Engineering' },
    FF: { label: 'FF', title: 'Facilities' },
    EHC: { label: 'EHC', title: 'External EHC Auditor' },
  };

  const config = codeConfig[code] || { label: code, title: code };

  return (
    <span className="responsibility-badge" title={config.title}>
      {config.label}
    </span>
  );
}

// Compute submission display status based on due dates
// Period ends → Due on 1st of next month → Past Due 2 weeks later
export function getSubmissionDisplayStatus(submission) {
  // If already approved, that's the status
  if (submission.status === 'approved') {
    return { status: 'approved', label: 'Approved', class: 'badge-green' };
  }

  // Parse period to determine due date
  const periodLabel = submission.period_label || '';
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  // Try to parse "Month Year" format (e.g., "January 2026")
  const monthMatch = periodLabel.match(/^(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})$/i);

  if (monthMatch) {
    const monthNames = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'];
    const monthIndex = monthNames.indexOf(monthMatch[1].toLowerCase());
    const year = parseInt(monthMatch[2]);

    // Due date: 1st of next month
    const dueDate = new Date(year, monthIndex + 1, 1);
    // Past due: 2 weeks after due date
    const pastDueDate = new Date(dueDate);
    pastDueDate.setDate(pastDueDate.getDate() + 14);

    if (today >= pastDueDate) {
      return { status: 'past_due', label: 'Past Due', class: 'badge-red' };
    } else if (today >= dueDate) {
      return { status: 'due', label: 'Due', class: 'badge-yellow' };
    } else {
      return { status: 'pending', label: 'Pending', class: 'badge-neutral' };
    }
  }

  // Try to parse quarterly "Q1 2026" format
  const quarterMatch = periodLabel.match(/^Q([1-4])\s+(\d{4})$/i);
  if (quarterMatch) {
    const quarter = parseInt(quarterMatch[1]);
    const year = parseInt(quarterMatch[2]);
    // Q1 ends Mar 31, Q2 ends Jun 30, Q3 ends Sep 30, Q4 ends Dec 31
    const quarterEndMonth = quarter * 3; // 3, 6, 9, 12
    const dueDate = new Date(year, quarterEndMonth, 1); // 1st of month after quarter
    const pastDueDate = new Date(dueDate);
    pastDueDate.setDate(pastDueDate.getDate() + 14);

    if (today >= pastDueDate) {
      return { status: 'past_due', label: 'Past Due', class: 'badge-red' };
    } else if (today >= dueDate) {
      return { status: 'due', label: 'Due', class: 'badge-yellow' };
    } else {
      return { status: 'pending', label: 'Pending', class: 'badge-neutral' };
    }
  }

  // Default: show actual status if can't parse
  const statusMap = {
    pending: { status: 'pending', label: 'Pending', class: 'badge-neutral' },
    in_progress: { status: 'in_progress', label: 'In Progress', class: 'badge-yellow' },
    submitted: { status: 'submitted', label: 'Submitted', class: 'badge-blue' },
    not_applicable: { status: 'not_applicable', label: 'N/A', class: 'badge-neutral' },
  };
  return statusMap[submission.status] || { status: submission.status, label: submission.status, class: 'badge-neutral' };
}

// Submission status badge with computed due date logic
export function SubmissionStatusBadge({ submission }) {
  const displayStatus = getSubmissionDisplayStatus(submission);
  return (
    <span className={`status-badge ${displayStatus.class}`} title={`DB status: ${submission.status}`}>
      {displayStatus.label}
    </span>
  );
}

// Compute submission stats from a list of submissions
export function computeSubmissionStats(subs) {
  const total = subs.length;
  let approved = 0, due = 0, pastDue = 0, pending = 0;

  subs.forEach(sub => {
    const displayStatus = getSubmissionDisplayStatus(sub);
    switch (displayStatus.status) {
      case 'approved': approved++; break;
      case 'due': due++; break;
      case 'past_due': pastDue++; break;
      default: pending++; break;
    }
  });

  return { total, approved, due, pastDue, pending };
}

// Record type badge
export function RecordTypeBadge({ type }) {
  const typeLabels = {
    daily: 'Daily',
    monthly: 'Monthly',
    bi_monthly: 'Bi-Monthly',
    quarterly: 'Quarterly',
    annual: 'Annual',
    one_time: 'One-Time',
    audit_window: 'Audit Window',
    as_needed: 'As Needed',
  };

  return (
    <span className="record-type-badge">
      {typeLabels[type] || type}
    </span>
  );
}
