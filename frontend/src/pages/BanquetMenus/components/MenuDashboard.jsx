import { Settings, FileDown } from 'lucide-react';
import { exportMenuToPdf } from '../utils/exportMenuPdf';

function MenuDashboard({ menu, menuCost, guestCount, onGuestCountChange, onEditClick }) {
  const handleExportPdf = () => {
    if (menu) {
      exportMenuToPdf(menu, menuCost, guestCount);
    }
  };
  const formatCurrency = (value) => {
    if (value === null || value === undefined) return '--';
    return `$${parseFloat(value).toFixed(2)}`;
  };

  const formatPercent = (value) => {
    if (value === null || value === undefined) return '--';
    return `${parseFloat(value).toFixed(1)}%`;
  };

  const getVarianceClass = (variance) => {
    if (variance === null || variance === undefined) return '';
    if (variance > 0) return 'positive'; // Under budget (good)
    if (variance < 0) return 'negative'; // Over budget (bad)
    return '';
  };

  const isBelowMinimum = menuCost && menuCost.min_guest_count && guestCount < menuCost.min_guest_count;

  return (
    <div className="menu-dashboard">
      <div className="dashboard-header">
        <h3 className="dashboard-title">Menu Overview</h3>
        <div className="dashboard-actions">
          <button className="btn-export-pdf" onClick={handleExportPdf} title="Export to PDF">
            <FileDown size={16} />
            Export PDF
          </button>
          <button className="btn-edit-dashboard" onClick={onEditClick}>
            <Settings size={16} />
            Edit Settings
          </button>
        </div>
      </div>

      <div className="dashboard-stats">
        <div className="stat-card">
          <div className="stat-label">Menu Price</div>
          <div className="stat-value">
            {formatCurrency(menu?.price_per_person)}/pp
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Menu Cost</div>
          <div className="stat-value">
            {formatCurrency(menuCost?.menu_cost_per_guest)}/pp
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Target FC%</div>
          <div className="stat-value">
            {formatPercent(menu?.target_food_cost_pct)}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Actual FC%</div>
          <div className={`stat-value ${menuCost?.actual_food_cost_pct > (menu?.target_food_cost_pct || 30) ? 'negative' : 'positive'}`}>
            {formatPercent(menuCost?.actual_food_cost_pct)}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Variance</div>
          <div className={`stat-value ${getVarianceClass(menuCost?.variance_pct)}`}>
            {menuCost?.variance_pct !== undefined && menuCost?.variance_pct !== null
              ? `${menuCost.variance_pct > 0 ? '+' : ''}${menuCost.variance_pct.toFixed(1)}%`
              : '--'}
          </div>
        </div>

        <div className="stat-card">
          <div className="stat-label">Total Revenue</div>
          <div className="stat-value">
            {formatCurrency(menuCost?.total_revenue)}
          </div>
        </div>
      </div>

      <div className="dashboard-guest-row">
        <div className="guest-input-group">
          <label>Guest Count:</label>
          <input
            type="number"
            className="guest-input"
            value={guestCount}
            onChange={onGuestCountChange}
            min="0"
          />
        </div>

        <div className="guest-input-group">
          <label>Min Guests:</label>
          <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600 }}>
            {menu?.min_guest_count || '--'}
          </span>
        </div>

        <div className={`surcharge-info ${isBelowMinimum ? 'active' : ''}`}>
          {isBelowMinimum ? (
            <>
              Surcharge: {formatCurrency(menuCost?.surcharge_total)}
              ({formatCurrency(menu?.under_min_surcharge)}/pp)
            </>
          ) : (
            menu?.under_min_surcharge
              ? `Surcharge ${formatCurrency(menu?.under_min_surcharge)}/pp applies below ${menu?.min_guest_count} guests`
              : 'No minimum guest surcharge configured'
          )}
        </div>
      </div>
    </div>
  );
}

export default MenuDashboard;
