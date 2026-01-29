import { useState } from 'react';
import axios from '../../../lib/axios';

function ImportMenuModal({ outletId, onClose, onImportComplete }) {
  const [csvText, setCsvText] = useState('');
  const [importing, setImporting] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);

  const parseCSV = (text) => {
    const lines = text.trim().split('\n');
    if (lines.length < 2) {
      throw new Error('CSV must have a header row and at least one data row');
    }

    // Parse header
    const header = lines[0].split(',').map(h => h.trim().toLowerCase());
    const requiredCols = ['meal_period', 'service_type', 'menu_name', 'menu_item'];

    for (const col of requiredCols) {
      if (!header.includes(col)) {
        throw new Error(`Missing required column: ${col}`);
      }
    }

    // Find column indices
    const colIdx = {
      meal_period: header.indexOf('meal_period'),
      service_type: header.indexOf('service_type'),
      menu_name: header.indexOf('menu_name'),
      menu_item: header.indexOf('menu_item'),
      prep_item: header.indexOf('prep_item'),
      choice_count: header.indexOf('choice_count')
    };

    // Parse data rows
    const items = [];
    for (let i = 1; i < lines.length; i++) {
      const line = lines[i].trim();
      if (!line) continue;

      // Handle quoted fields with commas
      const values = [];
      let current = '';
      let inQuotes = false;

      for (const char of line) {
        if (char === '"') {
          inQuotes = !inQuotes;
        } else if (char === ',' && !inQuotes) {
          values.push(current.trim());
          current = '';
        } else {
          current += char;
        }
      }
      values.push(current.trim());

      const item = {
        meal_period: values[colIdx.meal_period] || '',
        service_type: values[colIdx.service_type] || '',
        menu_name: values[colIdx.menu_name] || '',
        menu_item: values[colIdx.menu_item] || '',
        prep_item: colIdx.prep_item >= 0 ? values[colIdx.prep_item] || null : null,
        choice_count: colIdx.choice_count >= 0 && values[colIdx.choice_count]
          ? parseInt(values[colIdx.choice_count], 10) || null
          : null
      };

      if (item.meal_period && item.service_type && item.menu_name && item.menu_item) {
        items.push(item);
      }
    }

    return items;
  };

  const handleImport = async () => {
    setError(null);
    setResult(null);

    if (!csvText.trim()) {
      setError('Please paste CSV data');
      return;
    }

    let items;
    try {
      items = parseCSV(csvText);
    } catch (err) {
      setError(`CSV parsing error: ${err.message}`);
      return;
    }

    if (items.length === 0) {
      setError('No valid data rows found in CSV');
      return;
    }

    setImporting(true);
    try {
      const response = await axios.post('/banquet-menus/import', {
        outlet_id: outletId,
        items
      });

      setResult(response.data.stats);
    } catch (err) {
      console.error('Import error:', err);
      setError(err.response?.data?.detail || 'Import failed');
    } finally {
      setImporting(false);
    }
  };

  const handleDone = () => {
    onImportComplete();
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-wide" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Import Banquet Menus</h2>
          <button className="modal-close" onClick={onClose}>&times;</button>
        </div>

        <div className="modal-body">
          {error && <div className="error-message">{error}</div>}

          {result ? (
            <div className="import-results">
              <h3>Import Complete</h3>
              <div className="result-grid">
                <div className="result-item">
                  <span className="result-label">Menus Created:</span>
                  <span className="result-value success">{result.menus_created}</span>
                </div>
                <div className="result-item">
                  <span className="result-label">Menus Skipped (existing):</span>
                  <span className="result-value">{result.menus_skipped}</span>
                </div>
                <div className="result-item">
                  <span className="result-label">Menu Items Created:</span>
                  <span className="result-value success">{result.items_created}</span>
                </div>
                <div className="result-item">
                  <span className="result-label">Menu Items Skipped:</span>
                  <span className="result-value">{result.items_skipped}</span>
                </div>
                <div className="result-item">
                  <span className="result-label">Prep Items Created:</span>
                  <span className="result-value success">{result.prep_items_created}</span>
                </div>
                <div className="result-item">
                  <span className="result-label">Prep Items Skipped:</span>
                  <span className="result-value">{result.prep_items_skipped}</span>
                </div>
              </div>
              {result.errors && result.errors.length > 0 && (
                <div className="import-errors">
                  <h4>Errors:</h4>
                  <ul>
                    {result.errors.map((err, idx) => (
                      <li key={idx}>{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <>
              <p className="import-instructions">
                Paste CSV data with the following columns:
                <br />
                <code>meal_period, service_type, menu_name, menu_item, prep_item, choice_count</code>
                <br />
                <small>The prep_item and choice_count columns are optional.</small>
              </p>

              <textarea
                className="csv-input"
                value={csvText}
                onChange={(e) => setCsvText(e.target.value)}
                placeholder={`meal_period,service_type,menu_name,menu_item,prep_item,choice_count
Dinner,Buffet,Tuscan Table,Fresh Greens,Mixed Greens,
Dinner,Buffet,Tuscan Table,Fresh Ceviche – Choose Two,Shrimp Ceviche,2
...`}
                rows={15}
                disabled={importing}
              />
            </>
          )}
        </div>

        <div className="modal-footer">
          {result ? (
            <button type="button" className="btn-primary" onClick={handleDone}>
              Done
            </button>
          ) : (
            <>
              <button type="button" className="btn-secondary" onClick={onClose} disabled={importing}>
                Cancel
              </button>
              <button
                type="button"
                className="btn-primary"
                onClick={handleImport}
                disabled={importing || !csvText.trim()}
              >
                {importing ? 'Importing...' : 'Import'}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default ImportMenuModal;
