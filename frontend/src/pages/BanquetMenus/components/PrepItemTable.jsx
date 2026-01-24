import { useState, useEffect } from 'react';
import axios from '../../../lib/axios';
import { ChevronRight, Trash2, Link, Save, X } from 'lucide-react';
import UnitSelect from '../../../components/UnitSelect';
import AddPrepItemModal from './AddPrepItemModal';
import LinkPrepItemModal from './LinkPrepItemModal';

const AMOUNT_MODES = [
  { value: 'per_person', label: 'Per Person' },
  { value: 'at_minimum', label: 'At Minimum' },
  { value: 'fixed', label: 'Fixed' }
];

function PrepItemTable({ menuItemId, prepItems, itemCosts, guestCount, onPrepItemsChanged }) {
  const [expandedItems, setExpandedItems] = useState(new Set());
  const [editingItem, setEditingItem] = useState(null); // prep item id being edited
  const [editForm, setEditForm] = useState({});
  const [saving, setSaving] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [linkingPrepItem, setLinkingPrepItem] = useState(null);
  const [units, setUnits] = useState([]);

  // Load units for display
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
      // Cancel editing when collapsing
      if (editingItem === prepId) {
        setEditingItem(null);
        setEditForm({});
      }
    } else {
      newExpanded.add(prepId);
    }
    setExpandedItems(newExpanded);
  };

  const startEditing = (prep) => {
    setEditingItem(prep.id);
    setEditForm({
      name: prep.name || '',
      amount_mode: prep.amount_mode || 'per_person',
      amount_per_guest: prep.amount_per_guest || '',
      base_amount: prep.base_amount || '',
      unit_id: prep.unit_id || null,
      responsibility: prep.responsibility || ''
    });
  };

  const cancelEditing = () => {
    setEditingItem(null);
    setEditForm({});
  };

  const saveEditing = async () => {
    if (!editingItem) return;

    setSaving(true);
    try {
      const payload = {
        name: editForm.name,
        amount_mode: editForm.amount_mode,
        responsibility: editForm.responsibility || null,
        unit_id: editForm.unit_id || null
      };

      if (editForm.amount_mode === 'per_person') {
        payload.amount_per_guest = editForm.amount_per_guest ? parseFloat(editForm.amount_per_guest) : null;
        payload.base_amount = null;
      } else {
        payload.base_amount = editForm.base_amount ? parseFloat(editForm.base_amount) : null;
        payload.amount_per_guest = null;
      }

      await axios.put(`/banquet-menus/prep/${editingItem}`, payload);
      setEditingItem(null);
      setEditForm({});
      onPrepItemsChanged();
    } catch (err) {
      console.error('Error saving prep item:', err);
      alert('Failed to save changes');
    } finally {
      setSaving(false);
    }
  };

  const handleEditChange = (e) => {
    const { name, value } = e.target;
    setEditForm(prev => ({ ...prev, [name]: value }));
  };

  const getCostForPrepItem = (prepId) => {
    const costData = itemCosts.find(c => c.prep_item_id === prepId);
    return costData?.total_cost || 0;
  };

  const getUnitCostForPrepItem = (prepId) => {
    const costData = itemCosts.find(c => c.prep_item_id === prepId);
    return costData?.unit_cost || 0;
  };

  const isLinked = (prepItem) => {
    return prepItem.product_id || prepItem.recipe_id || prepItem.common_product_id;
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
            const isEditing = editingItem === prep.id;

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

                {/* Expanded Details */}
                {isExpanded && (
                  <div className="prep-item-details">
                    {isEditing ? (
                      /* Inline Edit Form */
                      <div className="prep-edit-form">
                        <div className="prep-edit-row">
                          <label>Name</label>
                          <input
                            type="text"
                            name="name"
                            className="form-input"
                            value={editForm.name}
                            onChange={handleEditChange}
                          />
                        </div>

                        <div className="prep-edit-row">
                          <label>Amount Type</label>
                          <select
                            name="amount_mode"
                            className="form-input"
                            value={editForm.amount_mode}
                            onChange={handleEditChange}
                          >
                            {AMOUNT_MODES.map(mode => (
                              <option key={mode.value} value={mode.value}>
                                {mode.label}
                              </option>
                            ))}
                          </select>
                        </div>

                        <div className="prep-edit-row">
                          <label>
                            {editForm.amount_mode === 'per_person' ? 'Amount Per Person' : 'Amount'}
                          </label>
                          <div className="prep-amount-input">
                            <input
                              type="number"
                              name={editForm.amount_mode === 'per_person' ? 'amount_per_guest' : 'base_amount'}
                              className="form-input"
                              value={editForm.amount_mode === 'per_person' ? editForm.amount_per_guest : editForm.base_amount}
                              onChange={handleEditChange}
                              step="0.0001"
                              min="0"
                            />
                            <UnitSelect
                              value={editForm.unit_id}
                              onChange={handleEditChange}
                              name="unit_id"
                            />
                          </div>
                        </div>

                        <div className="prep-edit-row">
                          <label>Responsibility</label>
                          <input
                            type="text"
                            name="responsibility"
                            className="form-input"
                            value={editForm.responsibility}
                            onChange={handleEditChange}
                            placeholder="e.g., Hot Line, Pantry"
                          />
                        </div>

                        <div className="prep-edit-actions">
                          <button
                            className="btn-secondary btn-sm"
                            onClick={cancelEditing}
                            disabled={saving}
                          >
                            <X size={14} /> Cancel
                          </button>
                          <button
                            className="btn-primary btn-sm"
                            onClick={saveEditing}
                            disabled={saving}
                          >
                            <Save size={14} /> {saving ? 'Saving...' : 'Save'}
                          </button>
                        </div>
                      </div>
                    ) : (
                      /* Read-only Details */
                      <div className="prep-detail-grid">
                        <div className="prep-detail-item">
                          <span className="prep-detail-label">Amount Type</span>
                          <span className="prep-detail-value">
                            {AMOUNT_MODES.find(m => m.value === (prep.amount_mode || 'per_person'))?.label}
                          </span>
                        </div>

                        <div className="prep-detail-item">
                          <span className="prep-detail-label">
                            {(prep.amount_mode || 'per_person') === 'per_person' ? 'Per Person' : 'Amount'}
                          </span>
                          <span className="prep-detail-value">
                            {(prep.amount_mode || 'per_person') === 'per_person'
                              ? (prep.amount_per_guest || '--')
                              : (prep.base_amount || '--')
                            } {prep.unit_abbr || getUnitAbbr(prep.unit_id) || prep.amount_unit || ''}
                          </span>
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

                        {prep.responsibility && (
                          <div className="prep-detail-item">
                            <span className="prep-detail-label">Responsibility</span>
                            <span className="prep-detail-value">{prep.responsibility}</span>
                          </div>
                        )}

                        <div className="prep-detail-actions">
                          <button
                            className="btn-secondary btn-sm"
                            onClick={() => startEditing(prep)}
                          >
                            Edit
                          </button>
                        </div>
                      </div>
                    )}
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
