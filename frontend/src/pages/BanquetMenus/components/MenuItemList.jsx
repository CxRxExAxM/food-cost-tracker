import { useState } from 'react';
import axios from 'axios';
import { ChevronRight, Edit2, Trash2 } from 'lucide-react';
import PrepItemTable from './PrepItemTable';
import AddItemModal from './AddItemModal';
import EditItemModal from './EditItemModal';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

function MenuItemList({ menuId, menuItems, itemCosts, guestCount, onItemsChanged }) {
  const [expandedItems, setExpandedItems] = useState(new Set());
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingItem, setEditingItem] = useState(null);

  const toggleExpand = (itemId) => {
    const newExpanded = new Set(expandedItems);
    if (newExpanded.has(itemId)) {
      newExpanded.delete(itemId);
    } else {
      newExpanded.add(itemId);
    }
    setExpandedItems(newExpanded);
  };

  const getCostForItem = (itemId) => {
    const costData = itemCosts.find(c => c.menu_item_id === itemId);
    return costData?.cost_per_guest || 0;
  };

  const handleDeleteItem = async (itemId, e) => {
    e.stopPropagation();
    if (!confirm('Are you sure you want to delete this menu item? All prep items will also be deleted.')) {
      return;
    }

    try {
      await axios.delete(`${API_URL}/api/banquet-menus/items/${itemId}`, {
        withCredentials: true
      });
      onItemsChanged();
    } catch (err) {
      console.error('Error deleting menu item:', err);
      alert('Failed to delete menu item');
    }
  };

  const handleItemAdded = () => {
    setShowAddModal(false);
    onItemsChanged();
  };

  const handleItemUpdated = () => {
    setEditingItem(null);
    onItemsChanged();
  };

  return (
    <div className="menu-items-section">
      <div className="section-header">
        <h3 className="section-title">Menu Items</h3>
        <button className="btn-add-item" onClick={() => setShowAddModal(true)}>
          + Add Item
        </button>
      </div>

      {menuItems.length === 0 ? (
        <div className="empty-state" style={{ borderRadius: 0 }}>
          No menu items yet. Click "Add Item" to get started.
        </div>
      ) : (
        <ul className="menu-item-list">
          {menuItems.map((item) => (
            <li key={item.id} className="menu-item-row">
              <div
                className="menu-item-header"
                onClick={() => toggleExpand(item.id)}
              >
                <div className="menu-item-left">
                  <span className={`expand-icon ${expandedItems.has(item.id) ? 'expanded' : ''}`}>
                    <ChevronRight size={16} />
                  </span>
                  <span className="menu-item-name">{item.name}</span>
                  {item.is_enhancement === 1 && (
                    <span className="enhancement-badge">Enhancement</span>
                  )}
                </div>

                <div className="menu-item-right">
                  <span className="item-cost">
                    ${getCostForItem(item.id).toFixed(2)}/guest
                  </span>
                  <div className="item-actions">
                    <button
                      className="btn-item-action"
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingItem(item);
                      }}
                      title="Edit item"
                    >
                      <Edit2 size={14} />
                    </button>
                    <button
                      className="btn-item-action delete"
                      onClick={(e) => handleDeleteItem(item.id, e)}
                      title="Delete item"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              </div>

              {expandedItems.has(item.id) && (
                <PrepItemTable
                  menuItemId={item.id}
                  prepItems={item.prep_items || []}
                  itemCosts={itemCosts.find(c => c.menu_item_id === item.id)?.prep_costs || []}
                  guestCount={guestCount}
                  onPrepItemsChanged={onItemsChanged}
                />
              )}
            </li>
          ))}
        </ul>
      )}

      {showAddModal && (
        <AddItemModal
          menuId={menuId}
          onClose={() => setShowAddModal(false)}
          onItemAdded={handleItemAdded}
        />
      )}

      {editingItem && (
        <EditItemModal
          item={editingItem}
          onClose={() => setEditingItem(null)}
          onItemUpdated={handleItemUpdated}
        />
      )}
    </div>
  );
}

export default MenuItemList;
