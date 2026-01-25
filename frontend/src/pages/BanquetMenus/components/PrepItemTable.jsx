import { useState, useEffect } from 'react';
import axios from '../../../lib/axios';
import { Trash2, Link } from 'lucide-react';
import AddPrepItemModal from './AddPrepItemModal';
import LinkPrepItemModal from './LinkPrepItemModal';

const AMOUNT_MODES = [
  { value: 'per_person', label: '/pp', fullLabel: 'Per Person' },
  { value: 'at_minimum', label: 'min', fullLabel: 'At Minimum' },
  { value: 'fixed', label: 'fixed', fullLabel: 'Fixed' }
];

function PrepItemTable({ menuItemId, prepItems, itemCosts, guestCount, onPrepItemsChanged }) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [linkingPrepItem, setLinkingPrepItem] = useState(null);
  const [units, setUnits] = useState([]);

  // Local copy of prep items for optimistic updates
  const [localPrepItems, setLocalPrepItems] = useState(prepItems);

  // Inline editing state
  const [editingCell, setEditingCell] = useState(null); // { prepId, field }
  const [editValue, setEditValue] = useState('');

  // Sync local state when props change (e.g., after add/delete/link)
  useEffect(() => {
    setLocalPrepItems(prepItems);
  }, [prepItems]);

  // Load units for display and editing
  useEffect(() => {
    const loadUnits = async () => {
      try {
        const response = await axios.get('/units');
        setUnits(response.data);
      } catch (err) {
        console.error('Error loading units:', err);
      }
    };
    loadUnits();
  }, []);

  const getUnitAbbr = (unitId) => {
    if (!unitId) return '';
    const unit = units.find(u => u.id === unitId);
    return unit?.abbreviation || '';
  };

  // Start editing a cell
  const startCellEdit = (prepId, field, currentValue) => {
    setEditingCell({ prepId, field });
    setEditValue(currentValue ?? '');
  };

  // Cancel editing
  const cancelCellEdit = () => {
    setEditingCell(null);
    setEditValue('');
  };

  // Save cell value on blur - update locally, save to server in background
  const handleCellSave = async (prepId, field) => {
    const prep = localPrepItems.find(p => p.id === prepId);
    if (!prep) {
      cancelCellEdit();
      return;
    }

    // Build update payload
    let updateData = {};
    let localUpdate = {};

    if (field === 'name') {
      const newValue = editValue || prep.name;
      updateData.name = newValue;
      localUpdate.name = newValue;
    } else if (field === 'amount_mode') {
      updateData.amount_mode = editValue;
      localUpdate.amount_mode = editValue;
      if (editValue === 'per_person') {
        updateData.base_amount = null;
        localUpdate.base_amount = null;
      } else {
        updateData.amount_per_guest = null;
        localUpdate.amount_per_guest = null;
      }
    } else if (field === 'amount_per_guest') {
      const numValue = editValue ? parseFloat(editValue) : null;
      updateData.amount_per_guest = numValue;
      localUpdate.amount_per_guest = numValue;
    } else if (field === 'base_amount') {
      const numValue = editValue ? parseFloat(editValue) : null;
      updateData.base_amount = numValue;
      localUpdate.base_amount = numValue;
    } else if (field === 'unit_id') {
      const numValue = editValue ? parseInt(editValue) : null;
      updateData.unit_id = numValue;
      localUpdate.unit_id = numValue;
      // Also update the display abbreviation
      localUpdate.unit_abbr = getUnitAbbr(numValue);
    }

    // Update local state immediately (optimistic update)
    setLocalPrepItems(prev => prev.map(p =>
      p.id === prepId ? { ...p, ...localUpdate } : p
    ));

    cancelCellEdit();

    // Save to server in background - don't trigger full reload for inline edits
    try {
      await axios.put(`/banquet-menus/prep/${prepId}`, updateData);
      // Note: Costs will be stale until next add/delete/link operation or page refresh
      // This is intentional to avoid jarring reloads during rapid editing
    } catch (err) {
      console.error('Error saving prep item:', err);
      // Revert on error
      setLocalPrepItems(prepItems);
    }
  };

  // Handle keyboard navigation
  const handleCellKeyDown = (e, prepId, field) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      cancelCellEdit();
      return;
    }

    if (e.key === 'Enter') {
      e.preventDefault();
      handleCellSave(prepId, field);
      return;
    }
  };

  const getCostForPrepItem = (prepId) => {
    const costData = itemCosts.find(c => c.prep_item_id === prepId);
    return costData?.total_cost || 0;
  };

  const getUnitCostForPrepItem = (prepId) => {
    const costData = itemCosts.find(c => c.prep_item_id === prepId);
    return costData?.unit_cost || 0;
  };

  const getLinkInfo = (prepItem) => {
    if (prepItem.common_product_id) {
      return { type: 'common', name: prepItem.common_product_name || 'Product' };
    }
    if (prepItem.product_id) {
      return { type: 'product', name: prepItem.product_name || 'Product' };
    }
    if (prepItem.recipe_id) {
      return { type: 'recipe', name: prepItem.recipe_name || 'Recipe' };
    }
    return null;
  };

  const handleDeletePrepItem = async (prepId) => {
    if (!confirm('Delete this prep item?')) {
      return;
    }

    try {
      await axios.delete(`/banquet-menus/prep/${prepId}`);
      onPrepItemsChanged();
    } catch (err) {
      console.error('Error deleting prep item:', err);
      alert('Failed to delete prep item');
    }
  };

  // Render an editable cell
  const renderEditableCell = (prep, field, displayValue, inputType = 'text', className = '') => {
    const isEditing = editingCell?.prepId === prep.id && editingCell?.field === field;

    if (isEditing) {
      if (field === 'amount_mode') {
        return (
          <select
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={() => handleCellSave(prep.id, field)}
            onKeyDown={(e) => handleCellKeyDown(e, prep.id, field)}
            className="prep-inline-select"
            autoFocus
          >
            {AMOUNT_MODES.map(mode => (
              <option key={mode.value} value={mode.value}>{mode.fullLabel}</option>
            ))}
          </select>
        );
      }

      if (field === 'unit_id') {
        return (
          <select
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            onBlur={() => handleCellSave(prep.id, field)}
            onKeyDown={(e) => handleCellKeyDown(e, prep.id, field)}
            className="prep-inline-select"
            autoFocus
          >
            <option value="">--</option>
            {units.map(u => (
              <option key={u.id} value={u.id}>{u.abbreviation}</option>
            ))}
          </select>
        );
      }

      return (
        <input
          type={inputType}
          value={editValue}
          onChange={(e) => setEditValue(e.target.value)}
          onBlur={() => handleCellSave(prep.id, field)}
          onKeyDown={(e) => handleCellKeyDown(e, prep.id, field)}
          onFocus={(e) => e.target.select()}
          className="prep-inline-input"
          autoFocus
          step={inputType === 'number' ? '0.0001' : undefined}
        />
      );
    }

    let editStartValue = displayValue;
    if (field === 'unit_id') {
      editStartValue = prep.unit_id;
    } else if (field === 'amount_mode') {
      editStartValue = prep.amount_mode || 'per_person';
    }

    return (
      <span
        className={`prep-editable-value ${className}`}
        onClick={() => startCellEdit(prep.id, field, editStartValue)}
        title="Click to edit"
      >
        {displayValue ?? '--'}
      </span>
    );
  };

  return (
    <div className="prep-items-container">
      {localPrepItems.length === 0 ? (
        <div className="prep-empty-state">
          No prep items yet. Click "Add Prep Item" below.
        </div>
      ) : (
        <table className="prep-items-table">
          <thead>
            <tr>
              <th>Prep Item</th>
              <th className="text-center">Amount</th>
              <th className="text-center">Type</th>
              <th>Linked To</th>
              <th className="text-right">Unit Cost</th>
              <th className="text-right">Total</th>
              <th className="text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {localPrepItems.map((prep) => {
              const linkInfo = getLinkInfo(prep);
              const unitCost = getUnitCostForPrepItem(prep.id);
              const totalCost = getCostForPrepItem(prep.id);
              const mode = prep.amount_mode || 'per_person';
              const unitAbbr = prep.unit_abbr || getUnitAbbr(prep.unit_id) || prep.amount_unit || '';
              const amountField = mode === 'per_person' ? 'amount_per_guest' : 'base_amount';
              const amountValue = mode === 'per_person' ? prep.amount_per_guest : prep.base_amount;
              const modeLabel = AMOUNT_MODES.find(m => m.value === mode)?.label || '';

              return (
                <tr key={prep.id}>
                  <td className="prep-name-cell">
                    {renderEditableCell(prep, 'name', prep.name)}
                  </td>
                  <td className="text-center prep-amount-cell">
                    <span className="prep-amount-group">
                      {renderEditableCell(prep, amountField, amountValue, 'number', 'amount-value')}
                      {renderEditableCell(prep, 'unit_id', unitAbbr || '--', 'text', 'amount-unit')}
                    </span>
                  </td>
                  <td className="text-center">
                    {renderEditableCell(prep, 'amount_mode', modeLabel, 'text', 'prep-mode-badge')}
                  </td>
                  <td className="prep-link-cell">
                    {linkInfo ? (
                      <span
                        className={`prep-link-badge ${linkInfo.type} clickable`}
                        onClick={() => setLinkingPrepItem(prep)}
                      >
                        {linkInfo.name}
                      </span>
                    ) : (
                      <button
                        className="btn-link-inline"
                        onClick={() => setLinkingPrepItem(prep)}
                      >
                        <Link size={12} /> Link
                      </button>
                    )}
                  </td>
                  <td className={`text-right prep-cost-cell ${!unitCost ? 'no-cost' : ''}`}>
                    {unitCost ? `$${unitCost.toFixed(2)}` : '--'}
                  </td>
                  <td className={`text-right prep-total-cell ${!totalCost ? 'no-cost' : ''}`}>
                    {totalCost ? `$${totalCost.toFixed(2)}` : '--'}
                  </td>
                  <td className="text-center prep-actions-cell">
                    <button
                      className="btn-prep-action delete"
                      onClick={() => handleDeletePrepItem(prep.id)}
                      title="Delete prep item"
                    >
                      <Trash2 size={14} />
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}

      <button className="btn-add-prep" onClick={() => setShowAddModal(true)}>
        + Add Prep Item
      </button>

      {showAddModal && (
        <AddPrepItemModal
          menuItemId={menuItemId}
          onClose={() => setShowAddModal(false)}
          onPrepItemAdded={() => {
            setShowAddModal(false);
            onPrepItemsChanged();
          }}
        />
      )}

      {linkingPrepItem && (
        <LinkPrepItemModal
          prepItem={linkingPrepItem}
          onClose={() => setLinkingPrepItem(null)}
          onLinked={() => {
            setLinkingPrepItem(null);
            onPrepItemsChanged();
          }}
        />
      )}
    </div>
  );
}

export default PrepItemTable;
