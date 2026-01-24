import { useState, useEffect } from 'react';
import axios from '../../../lib/axios';
import { ChevronRight, Trash2, Link } from 'lucide-react';
import AddPrepItemModal from './AddPrepItemModal';
import LinkPrepItemModal from './LinkPrepItemModal';

const AMOUNT_MODES = [
  { value: 'per_person', label: 'Per Person' },
  { value: 'at_minimum', label: 'At Minimum' },
  { value: 'fixed', label: 'Fixed' }
];

function PrepItemTable({ menuItemId, prepItems, itemCosts, guestCount, onPrepItemsChanged }) {
  const [expandedItems, setExpandedItems] = useState(new Set());
  const [showAddModal, setShowAddModal] = useState(false);
  const [linkingPrepItem, setLinkingPrepItem] = useState(null);
  const [units, setUnits] = useState([]);

  // Inline editing state (like Products page)
  const [editingCell, setEditingCell] = useState(null); // { prepId, field }
  const [editValue, setEditValue] = useState('');

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

  const toggleExpand = (prepId) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(prepId)) {
      newExpanded.delete(prepId);
      // Cancel any editing when collapsing
      if (editingCell?.prepId === prepId) {
        setEditingCell(null);
        setEditValue('');
      }
    } else {
      newExpanded.add(prepId);
    }
    setExpandedItems(newExpanded);
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

  // Save cell value on blur
  const handleCellSave = async (prepId, field) => {
    const prep = prepItems.find(p => p.id === prepId);
    if (!prep) {
      cancelCellEdit();
      return;
    }

    try {
      let updateData = {};

      // Build update payload based on field
      if (field === 'name') {
        updateData.name = editValue || prep.name;
      } else if (field === 'amount_mode') {
        updateData.amount_mode = editValue;
        // Clear the opposite amount field when changing mode
        if (editValue === 'per_person') {
          updateData.base_amount = null;
        } else {
          updateData.amount_per_guest = null;
        }
      } else if (field === 'amount_per_guest') {
        updateData.amount_per_guest = editValue ? parseFloat(editValue) : null;
      } else if (field === 'base_amount') {
        updateData.base_amount = editValue ? parseFloat(editValue) : null;
      } else if (field === 'unit_id') {
        updateData.unit_id = editValue ? parseInt(editValue) : null;
      } else if (field === 'responsibility') {
        updateData.responsibility = editValue || null;
      }

      await axios.put(`/banquet-menus/prep/${prepId}`, updateData);
      onPrepItemsChanged();
    } catch (err) {
      console.error('Error saving prep item:', err);
    } finally {
      cancelCellEdit();
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

    // Tab moves to next editable field
    if (e.key === 'Tab') {
      e.preventDefault();
      const prep = prepItems.find(p => p.id === prepId);
      if (!prep) return;

      const mode = prep.amount_mode || 'per_person';
      const amountField = mode === 'per_person' ? 'amount_per_guest' : 'base_amount';
      const fields = ['name', 'amount_mode', amountField, 'unit_id', 'responsibility'];
      const currentIdx = fields.indexOf(field);
      const nextIdx = e.shiftKey ? currentIdx - 1 : currentIdx + 1;

      if (nextIdx >= 0 && nextIdx < fields.length) {
        const nextField = fields[nextIdx];
        handleCellSave(prepId, field).then(() => {
          // Wait a tick for state to update, then start editing next field
          setTimeout(() => {
            const updatedPrep = prepItems.find(p => p.id === prepId);
            if (updatedPrep) {
              let nextValue;
              if (nextField === 'unit_id') {
                nextValue = updatedPrep.unit_id;
              } else {
                nextValue = updatedPrep[nextField];
              }
              startCellEdit(prepId, nextField, nextValue);
            }
          }, 50);
        });
      } else {
        handleCellSave(prepId, field);
      }
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

  const handleDeletePrepItem = async (prepId, e) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this prep item?')) {
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

  const formatAmount = (prep) => {
    const mode = prep.amount_mode || 'per_person';
    const unitAbbr = prep.unit_abbr || getUnitAbbr(prep.unit_id) || prep.amount_unit || '';

    if (mode === 'per_person') {
      const amt = prep.amount_per_guest;
      return amt ? `${amt} ${unitAbbr}/person` : '--';
    } else {
      const amt = prep.base_amount;
      const modeLabel = mode === 'at_minimum' ? 'min' : 'fixed';
      return amt ? `${amt} ${unitAbbr} (${modeLabel})` : '--';
    }
  };

  // Render an editable cell
  const renderEditableCell = (prep, field, displayValue, inputType = 'text') => {
    const isEditing = editingCell?.prepId === prep.id && editingCell?.field === field;

    if (isEditing) {
      // Special handling for select fields
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
              <option key={mode.value} value={mode.value}>{mode.label}</option>
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

      // Standard input field
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

    // Determine what value to pass when starting edit
    let editStartValue = displayValue;
    if (field === 'unit_id') {
      editStartValue = prep.unit_id;
    } else if (field === 'amount_mode') {
      editStartValue = prep.amount_mode || 'per_person';
    }

    return (
      <span
        className="prep-editable-value"
        onClick={(e) => {
          e.stopPropagation();
          startCellEdit(prep.id, field, editStartValue);
        }}
        title="Click to edit"
      >
        {displayValue ?? '--'}
      </span>
    );
  };

  return (
    <div className="prep-items-container">
      {prepItems.length === 0 ? (
        <div className="prep-empty-state">
          No prep items yet. Click "Add Prep Item" below.
        </div>
      ) : (
        <ul className="prep-item-list">
          {prepItems.map((prep) => {
            const linkInfo = getLinkInfo(prep);
            const unitCost = getUnitCostForPrepItem(prep.id);
            const totalCost = getCostForPrepItem(prep.id);
            const isExpanded = expandedItems.has(prep.id);
            const mode = prep.amount_mode || 'per_person';
            const unitAbbr = prep.unit_abbr || getUnitAbbr(prep.unit_id) || prep.amount_unit || '';

            return (
              <li key={prep.id} className="prep-item-row">
                {/* Collapsed Header */}
                <div
                  className="prep-item-header"
                  onClick={() => toggleExpand(prep.id)}
                >
                  <div className="prep-item-left">
                    <span className={`expand-icon ${isExpanded ? 'expanded' : ''}`}>
                      <ChevronRight size={14} />
                    </span>
                    <span className="prep-item-name">{prep.name}</span>
                  </div>

                  <div className="prep-item-summary">
                    <span className="prep-amount">{formatAmount(prep)}</span>
                    {linkInfo && (
                      <span className={`prep-link-badge ${linkInfo.type}`}>
                        {linkInfo.name}
                      </span>
                    )}
                    <span className={`prep-cost ${!unitCost ? 'no-cost' : ''}`}>
                      {unitCost ? `$${unitCost.toFixed(2)}/unit` : '--'}
                    </span>
                  </div>

                  <div className="prep-item-actions" onClick={e => e.stopPropagation()}>
                    <button
                      className="btn-prep-action delete"
                      onClick={(e) => handleDeletePrepItem(prep.id, e)}
                      title="Delete prep item"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>

                {/* Expanded Details - Click to Edit */}
                {isExpanded && (
                  <div className="prep-item-details">
                    <div className="prep-detail-grid">
                      <div className="prep-detail-item">
                        <span className="prep-detail-label">Name</span>
                        {renderEditableCell(prep, 'name', prep.name)}
                      </div>

                      <div className="prep-detail-item">
                        <span className="prep-detail-label">Amount Type</span>
                        {renderEditableCell(
                          prep,
                          'amount_mode',
                          AMOUNT_MODES.find(m => m.value === mode)?.label
                        )}
                      </div>

                      <div className="prep-detail-item">
                        <span className="prep-detail-label">
                          {mode === 'per_person' ? 'Per Person' : 'Amount'}
                        </span>
                        {renderEditableCell(
                          prep,
                          mode === 'per_person' ? 'amount_per_guest' : 'base_amount',
                          mode === 'per_person' ? prep.amount_per_guest : prep.base_amount,
                          'number'
                        )}
                      </div>

                      <div className="prep-detail-item">
                        <span className="prep-detail-label">Unit</span>
                        {renderEditableCell(prep, 'unit_id', unitAbbr || '--')}
                      </div>

                      <div className="prep-detail-item">
                        <span className="prep-detail-label">Unit Cost</span>
                        <span className="prep-detail-value">
                          {unitCost ? `$${unitCost.toFixed(4)}` : '--'}
                        </span>
                      </div>

                      <div className="prep-detail-item">
                        <span className="prep-detail-label">Total ({guestCount}g)</span>
                        <span className="prep-detail-value prep-detail-total">
                          {totalCost ? `$${totalCost.toFixed(2)}` : '--'}
                        </span>
                      </div>

                      <div className="prep-detail-item">
                        <span className="prep-detail-label">Linked To</span>
                        <span className="prep-detail-value">
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
                              <Link size={12} /> Link Product
                            </button>
                          )}
                        </span>
                      </div>

                      <div className="prep-detail-item">
                        <span className="prep-detail-label">Responsibility</span>
                        {renderEditableCell(prep, 'responsibility', prep.responsibility || '--')}
                      </div>
                    </div>
                  </div>
                )}
              </li>
            );
          })}
        </ul>
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
