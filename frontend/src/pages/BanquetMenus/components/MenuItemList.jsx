import { useState, useRef } from 'react';
import axios from '../../../lib/axios';
import { ChevronRight, Edit2, Trash2, GripVertical } from 'lucide-react';
import PrepItemTable from './PrepItemTable';
import AddItemModal from './AddItemModal';
import EditItemModal from './EditItemModal';

function MenuItemList({ menuId, menuItems, itemCosts, guestCount, expandedItems, onToggleExpand, onItemsChanged, onInlineEdit, menuType = 'banquet' }) {
  const isRestaurant = menuType === 'restaurant';
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingItem, setEditingItem] = useState(null);

  // Drag and drop state
  const [draggedItem, setDraggedItem] = useState(null);
  const [dragOverItem, setDragOverItem] = useState(null);
  const dragNodeRef = useRef(null);

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
      await axios.delete(`/banquet-menus/items/${itemId}`);
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

  // Drag and drop handlers
  const handleDragStart = (e, item, index) => {
    setDraggedItem({ item, index });
    dragNodeRef.current = e.target;
    e.target.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragEnd = (e) => {
    e.target.classList.remove('dragging');
    setDraggedItem(null);
    setDragOverItem(null);
    dragNodeRef.current = null;
  };

  const handleDragOver = (e, index) => {
    e.preventDefault();
    if (draggedItem === null || draggedItem.index === index) return;
    setDragOverItem(index);
  };

  const handleDragLeave = () => {
    setDragOverItem(null);
  };

  const handleDrop = async (e, targetIndex) => {
    e.preventDefault();
    if (draggedItem === null || draggedItem.index === targetIndex) {
      setDragOverItem(null);
      return;
    }

    // Calculate new order
    const items = [...menuItems];
    const [removed] = items.splice(draggedItem.index, 1);
    items.splice(targetIndex, 0, removed);

    // Build reorder payload with new display_order values
    const reorderPayload = items.map((item, idx) => ({
      id: item.id,
      display_order: idx
    }));

    setDragOverItem(null);

    try {
      await axios.patch('/banquet-menus/items/reorder', reorderPayload);
      onItemsChanged();
    } catch (err) {
      console.error('Error reordering items:', err);
    }
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
          {menuItems.map((item, index) => (
            <li
              key={item.id}
              className={`menu-item-row ${dragOverItem === index ? 'drag-over' : ''}`}
              draggable
              onDragStart={(e) => handleDragStart(e, item, index)}
              onDragEnd={handleDragEnd}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragLeave={handleDragLeave}
              onDrop={(e) => handleDrop(e, index)}
            >
              <div
                className="menu-item-header"
                onClick={() => onToggleExpand(item.id)}
              >
                <div className="menu-item-left">
                  <span
                    className="drag-handle"
                    onMouseDown={(e) => e.stopPropagation()}
                    title="Drag to reorder"
                  >
                    <GripVertical size={16} />
                  </span>
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
                    ${getCostForItem(item.id).toFixed(2)}{isRestaurant ? '' : '/guest'}
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
                  onInlineEdit={onInlineEdit}
                  menuType={menuType}
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
