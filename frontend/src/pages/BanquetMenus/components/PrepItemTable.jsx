import { useState } from 'react';
import axios from 'axios';
import { Edit2, Trash2, Link } from 'lucide-react';
import AddPrepItemModal from './AddPrepItemModal';
import EditPrepItemModal from './EditPrepItemModal';
import LinkPrepItemModal from './LinkPrepItemModal';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function PrepItemTable({ menuItemId, prepItems, itemCosts, guestCount, onPrepItemsChanged }) {
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingPrepItem, setEditingPrepItem] = useState(null);
  const [linkingPrepItem, setLinkingPrepItem] = useState(null);

  const getCostForPrepItem = (prepId) => {
    const costData = itemCosts.find(c => c.prep_item_id === prepId);
    return costData?.total_cost || 0;
  };

  const getUnitCostForPrepItem = (prepId) => {
    const costData = itemCosts.find(c => c.prep_item_id === prepId);
    return costData?.unit_cost || 0;
  };

  const isLinked = (prepItem) => {
    return prepItem.product_id || prepItem.recipe_id;
  };

  const getLinkInfo = (prepItem) => {
    if (prepItem.product_id) {
      return { type: 'product', name: prepItem.product_name || 'Product' };
    }
    if (prepItem.recipe_id) {
      return { type: 'recipe', name: prepItem.recipe_name || 'Recipe' };
    }
    return null;
  };

  const handleDeletePrepItem = async (prepId) => {
    if (!confirm('Are you sure you want to delete this prep item?')) {
      return;
    }

    try {
      await axios.delete(`${API_URL}/api/banquet-menus/prep/${prepId}`, {
        withCredentials: true
      });
      onPrepItemsChanged();
    } catch (err) {
      console.error('Error deleting prep item:', err);
      alert('Failed to delete prep item');
    }
  };

  const handlePrepItemAdded = () => {
    setShowAddModal(false);
    onPrepItemsChanged();
  };

  const handlePrepItemUpdated = () => {
    setEditingPrepItem(null);
    onPrepItemsChanged();
  };

  const handlePrepItemLinked = () => {
    setLinkingPrepItem(null);
    onPrepItemsChanged();
  };

  return (
    <div className="prep-items-container">
      <table className="prep-items-table">
        <thead>
          <tr>
            <th>Prep Item</th>
            <th>Amount</th>
            <th>Linked To</th>
            <th>Unit Cost</th>
            <th>Total ({guestCount}g)</th>
            <th style={{ width: '80px' }}></th>
          </tr>
        </thead>
        <tbody>
          {prepItems.length === 0 ? (
            <tr>
              <td colSpan="6" style={{ textAlign: 'center', color: 'var(--text-tertiary)', padding: 'var(--space-6)' }}>
                No prep items yet. Click "Add Prep Item" below.
              </td>
            </tr>
          ) : (
            prepItems.map((prep) => {
              const linkInfo = getLinkInfo(prep);
              const unitCost = getUnitCostForPrepItem(prep.id);
              const totalCost = getCostForPrepItem(prep.id);

              return (
                <tr key={prep.id}>
                  <td>{prep.name}</td>
                  <td>
                    {prep.amount_per_guest
                      ? `${prep.amount_per_guest} ${prep.amount_unit || ''}`
                      : '--'}
                  </td>
                  <td>
                    {linkInfo ? (
                      <span
                        className={`link-badge ${linkInfo.type}`}
                        onClick={() => setLinkingPrepItem(prep)}
                        style={{ cursor: 'pointer' }}
                        title="Click to change link"
                      >
                        {linkInfo.name}
                      </span>
                    ) : (
                      <button
                        className="btn-link-prep"
                        onClick={() => setLinkingPrepItem(prep)}
                      >
                        <Link size={12} style={{ marginRight: '4px' }} />
                        Link
                      </button>
                    )}
                  </td>
                  <td className={`cost-cell ${!unitCost ? 'no-cost' : ''}`}>
                    {unitCost ? `$${unitCost.toFixed(4)}` : '--'}
                  </td>
                  <td className={`cost-cell ${!totalCost ? 'no-cost' : ''}`}>
                    {totalCost ? `$${totalCost.toFixed(2)}` : '--'}
                  </td>
                  <td>
                    <div className="item-actions">
                      <button
                        className="btn-item-action"
                        onClick={() => setEditingPrepItem(prep)}
                        title="Edit prep item"
                      >
                        <Edit2 size={12} />
                      </button>
                      <button
                        className="btn-item-action delete"
                        onClick={() => handleDeletePrepItem(prep.id)}
                        title="Delete prep item"
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })
          )}
        </tbody>
      </table>

      <button className="btn-add-prep" onClick={() => setShowAddModal(true)}>
        + Add Prep Item
      </button>

      {showAddModal && (
        <AddPrepItemModal
          menuItemId={menuItemId}
          onClose={() => setShowAddModal(false)}
          onPrepItemAdded={handlePrepItemAdded}
        />
      )}

      {editingPrepItem && (
        <EditPrepItemModal
          prepItem={editingPrepItem}
          onClose={() => setEditingPrepItem(null)}
          onPrepItemUpdated={handlePrepItemUpdated}
        />
      )}

      {linkingPrepItem && (
        <LinkPrepItemModal
          prepItem={linkingPrepItem}
          onClose={() => setLinkingPrepItem(null)}
          onLinked={handlePrepItemLinked}
        />
      )}
    </div>
  );
}

export default PrepItemTable;
