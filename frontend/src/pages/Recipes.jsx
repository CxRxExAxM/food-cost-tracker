import { useState, useEffect, useRef } from 'react';
import axios from '../lib/axios';
import Navigation from '../components/Navigation';
import { useOutlet } from '../contexts/OutletContext';
import OutletBadge from '../components/outlets/OutletBadge';
import UploadRecipeModal from '../components/RecipeImport/UploadRecipeModal';
import ReviewParsedRecipe from '../components/RecipeImport/ReviewParsedRecipe';
import './Recipes.css';

const API_URL = import.meta.env.VITE_API_URL ?? '';

// Allergen definitions with icons
const ALLERGEN_ICONS = {
  'Gluten': '🌾',
  'Dairy': '🥛',
  'Egg': '🥚',
  'Fish': '🐟',
  'Crustation': '🦐',
  'Mollusk': '🦪',
  'Tree Nuts': '🌰',
  'Peanuts': '🥜',
  'Soy': '🫘',
  'Sesame': '⚪',
  'Mustard': '🟡',
  'Celery': '🥬',
  'Lupin': '🌸',
  'Sulphur Dioxide': '🧪'
};

function Recipes() {
  const { currentOutlet } = useOutlet();
  const [recipes, setRecipes] = useState([]);
  const [selectedRecipe, setSelectedRecipe] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expandedFolders, setExpandedFolders] = useState(new Set());
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showFolderModal, setShowFolderModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [showReviewModal, setShowReviewModal] = useState(false);
  const [parseResult, setParseResult] = useState(null);
  const [editedRecipe, setEditedRecipe] = useState(null);
  const [isDirty, setIsDirty] = useState(false);
  const [contextMenu, setContextMenu] = useState(null);
  const [renamingFolder, setRenamingFolder] = useState(null);
  const [draggedItem, setDraggedItem] = useState(null);
  const [dropTarget, setDropTarget] = useState(null);
  const [prefilledCategoryPath, setPrefilledCategoryPath] = useState('');
  const [virtualFolders, setVirtualFolders] = useState(() => {
    // Load from localStorage on mount
    const saved = localStorage.getItem('virtualFolders');
    return saved ? JSON.parse(saved) : [];
  });

  useEffect(() => {
    fetchRecipes();
  }, [currentOutlet]);

  const fetchRecipes = async () => {
    try {
      setLoading(true);
      const params = {};
      // Filter by outlet if specific outlet selected (not "All Outlets")
      if (currentOutlet && currentOutlet.id !== 'all') {
        params.outlet_id = currentOutlet.id;
      }
      const response = await axios.get(`${API_URL}/recipes`, { params });
      setRecipes(response.data);
    } catch (error) {
      console.error('Error fetching recipes:', error);
    } finally {
      setLoading(false);
    }
  };

  // Build tree structure from recipes + virtual folders
  const buildTree = () => {
    const tree = [];
    const folderMap = new Map(); // Track folders by path

    // Filter out placeholder recipes (folder markers)
    const realRecipes = recipes.filter(r => !r.name.startsWith('.folder_'));

    // First, create all virtual folders (empty folders)
    virtualFolders.forEach(folderPath => {
      const segments = folderPath.split('/').filter(s => s.trim());
      let currentPath = '';
      let currentLevel = tree;

      segments.forEach((segment, index) => {
        currentPath = currentPath ? `${currentPath}/${segment}` : segment;

        let folder = currentLevel.find(
          item => item.type === 'folder' && item.path === currentPath
        );

        if (!folder) {
          folder = {
            type: 'folder',
            name: segment,
            path: currentPath,
            children: [],
            isVirtual: true
          };
          currentLevel.push(folder);
        }

        currentLevel = folder.children;
      });
    });

    // Then add recipes and their folder structures
    realRecipes.forEach(recipe => {
      const path = recipe.category_path || '';

      if (!path) {
        // Root level recipe
        tree.push({ type: 'recipe', data: recipe });
        return;
      }

      // Split path into folder segments
      const segments = path.split('/').filter(s => s.trim());
      let currentPath = '';
      let currentLevel = tree;

      // Build folder hierarchy
      segments.forEach((segment, index) => {
        currentPath = currentPath ? `${currentPath}/${segment}` : segment;

        // Check if folder exists at this level
        let folder = currentLevel.find(
          item => item.type === 'folder' && item.path === currentPath
        );

        if (!folder) {
          // Create new folder
          folder = {
            type: 'folder',
            name: segment,
            path: currentPath,
            children: [],
            isVirtual: false
          };
          currentLevel.push(folder);
        } else if (folder.isVirtual) {
          // Mark as non-virtual once it has recipes
          folder.isVirtual = false;
        }

        // If this is the last segment, add the recipe to this folder
        if (index === segments.length - 1) {
          folder.children.push({ type: 'recipe', data: recipe });
        } else {
          // Move to next level
          currentLevel = folder.children;
        }
      });
    });

    // Sort: folders first, then recipes, alphabetically
    const sortTree = (items) => {
      items.sort((a, b) => {
        if (a.type === 'folder' && b.type === 'recipe') return -1;
        if (a.type === 'recipe' && b.type === 'folder') return 1;

        const nameA = a.type === 'folder' ? a.name : a.data.name;
        const nameB = b.type === 'folder' ? b.name : b.data.name;
        return nameA.localeCompare(nameB);
      });

      items.forEach(item => {
        if (item.type === 'folder' && item.children) {
          sortTree(item.children);
        }
      });
    };

    sortTree(tree);
    return tree;
  };

  const toggleFolder = (path) => {
    const newExpanded = new Set(expandedFolders);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpandedFolders(newExpanded);
  };

  const selectRecipe = async (recipeId) => {
    try {
      const response = await axios.get(`${API_URL}/recipes/${recipeId}`);
      setSelectedRecipe(response.data);
      setEditedRecipe({});
      setIsDirty(false);
    } catch (error) {
      console.error('Error fetching recipe:', error);
    }
  };

  const createNewRecipe = () => {
    setPrefilledCategoryPath('');
    setShowCreateModal(true);
  };

  const handleUploadDocument = () => {
    // Check if outlet is selected
    if (!currentOutlet || currentOutlet.id === 'all') {
      alert('Please select a specific outlet before uploading recipes');
      return;
    }

    // Additional validation: ensure we have a valid numeric outlet ID
    if (!currentOutlet.id || typeof currentOutlet.id !== 'number') {
      console.error('Invalid outlet ID:', currentOutlet);
      alert('Outlet ID is invalid. Please select an outlet from the dropdown and try again.');
      return;
    }

    console.log('Opening upload modal with outlet ID:', currentOutlet.id);
    setShowUploadModal(true);
  };

  const handleParseComplete = (result) => {
    setParseResult(result);
    setShowUploadModal(false);
    setShowReviewModal(true);
  };

  const handleReviewClose = () => {
    setShowReviewModal(false);
    setParseResult(null);
    // Refresh recipes list
    fetchRecipes();
  };

  const createNewFolder = () => {
    setShowFolderModal(true);
  };

  const handleCreateFolder = (folderPath) => {
    // Add to virtual folders
    const newVirtualFolders = [...virtualFolders, folderPath];
    setVirtualFolders(newVirtualFolders);
    localStorage.setItem('virtualFolders', JSON.stringify(newVirtualFolders));

    // Expand the folder to show it
    const newExpanded = new Set(expandedFolders);
    const segments = folderPath.split('/').filter(s => s.trim());
    let currentPath = '';
    segments.forEach(segment => {
      currentPath = currentPath ? `${currentPath}/${segment}` : segment;
      newExpanded.add(currentPath);
    });
    setExpandedFolders(newExpanded);

    // Close modal
    setShowFolderModal(false);
  };

  const handleCreateRecipe = async (newRecipe) => {
    try {
      // Extract outlet_id for query param
      const { outlet_id, ...recipeData } = newRecipe;

      // Build URL with outlet_id as query parameter
      let url = `${API_URL}/recipes`;
      if (outlet_id) {
        url += `?outlet_id=${outlet_id}`;
      }

      const response = await axios.post(url, recipeData);
      setRecipes([...recipes, response.data]);
      setShowCreateModal(false);
      selectRecipe(response.data.id);
    } catch (error) {
      console.error('Error creating recipe:', error);
      alert('Failed to create recipe');
    }
  };

  const handleUpdateRecipe = async () => {
    if (!editedRecipe || !selectedRecipe) return;

    try {
      await axios.patch(`${API_URL}/recipes/${selectedRecipe.id}`, editedRecipe);

      // Update recipes list
      setRecipes(recipes.map(r => r.id === selectedRecipe.id ? { ...r, ...editedRecipe } : r));

      // Update selected recipe
      setSelectedRecipe({ ...selectedRecipe, ...editedRecipe });
      setEditedRecipe(null);
      setIsDirty(false);
    } catch (error) {
      console.error('Error updating recipe:', error);
      alert('Failed to update recipe');
    }
  };

  const handleDeleteRecipe = async (recipeId) => {
    if (!confirm('Are you sure you want to delete this recipe?')) return;

    try {
      await axios.delete(`${API_URL}/recipes/${recipeId}`);
      setRecipes(recipes.filter(r => r.id !== recipeId));
      setSelectedRecipe(null);
      setEditedRecipe(null);
    } catch (error) {
      console.error('Error deleting recipe:', error);
      alert('Failed to delete recipe');
    }
  };

  const handleFieldChange = (field, value) => {
    setEditedRecipe({ ...editedRecipe, [field]: value });
    setIsDirty(true);
  };

  const handleCancel = () => {
    if (isDirty && !confirm('You have unsaved changes. Are you sure you want to cancel?')) {
      return;
    }
    setEditedRecipe(null);
    setIsDirty(false);
  };

  const handleContextMenu = (e, item) => {
    e.preventDefault();
    e.stopPropagation();
    setContextMenu({
      x: e.clientX,
      y: e.clientY,
      item: item
    });
  };

  const closeContextMenu = () => {
    setContextMenu(null);
  };

  const handleRenameFolder = (folderPath) => {
    const newName = prompt('Enter new folder name:', folderPath.split('/').pop());
    if (!newName || !newName.trim()) return;

    // Get all recipes in this folder and update their paths
    const pathPrefix = folderPath + '/';
    const recipesToUpdate = recipes.filter(r =>
      r.category_path === folderPath || r.category_path?.startsWith(pathPrefix)
    );

    if (recipesToUpdate.length === 0) {
      alert('No recipes in this folder');
      return;
    }

    // Calculate new path
    const parentPath = folderPath.split('/').slice(0, -1).join('/');
    const newPath = parentPath ? `${parentPath}/${newName.trim()}` : newName.trim();

    // Update all affected recipes
    Promise.all(
      recipesToUpdate.map(recipe => {
        let newCategoryPath;
        if (recipe.category_path === folderPath) {
          newCategoryPath = newPath;
        } else {
          newCategoryPath = recipe.category_path.replace(folderPath, newPath);
        }

        return axios.patch(`${API_URL}/recipes/${recipe.id}`, {
          category_path: newCategoryPath
        });
      })
    )
      .then(() => {
        fetchRecipes();
        closeContextMenu();
      })
      .catch(error => {
        console.error('Error renaming folder:', error);
        alert('Failed to rename folder');
      });
  };

  const handleDeleteFolder = (folderPath) => {
    const recipesInFolder = recipes.filter(r =>
      r.category_path === folderPath || r.category_path?.startsWith(folderPath + '/')
    );

    if (recipesInFolder.length === 0) {
      // Empty virtual folder - just remove it
      if (!confirm(`Delete empty folder "${folderPath}"?`)) {
        return;
      }

      const newVirtualFolders = virtualFolders.filter(vf => vf !== folderPath && !vf.startsWith(folderPath + '/'));
      setVirtualFolders(newVirtualFolders);
      localStorage.setItem('virtualFolders', JSON.stringify(newVirtualFolders));
      closeContextMenu();
      return;
    }

    if (!confirm(`Delete folder and move ${recipesInFolder.length} recipe(s) to root?`)) {
      return;
    }

    Promise.all(
      recipesInFolder.map(recipe => {
        // Remove the folder path, keeping any sub-path
        const remainingPath = recipe.category_path.replace(folderPath, '').replace(/^\//, '');
        return axios.patch(`${API_URL}/recipes/${recipe.id}`, {
          category_path: remainingPath || null
        });
      })
    )
      .then(() => {
        // Also remove from virtual folders
        const newVirtualFolders = virtualFolders.filter(vf => vf !== folderPath && !vf.startsWith(folderPath + '/'));
        setVirtualFolders(newVirtualFolders);
        localStorage.setItem('virtualFolders', JSON.stringify(newVirtualFolders));

        fetchRecipes();
        closeContextMenu();
      })
      .catch(error => {
        console.error('Error deleting folder:', error);
        alert('Failed to delete folder');
      });
  };

  // Close context menu when clicking outside
  useEffect(() => {
    const handleClick = () => closeContextMenu();
    if (contextMenu) {
      document.addEventListener('click', handleClick);
      return () => document.removeEventListener('click', handleClick);
    }
  }, [contextMenu]);

  // Drag and drop handlers
  const handleDragStart = (e, item) => {
    if (item.type === 'recipe') {
      setDraggedItem(item);
      e.dataTransfer.effectAllowed = 'move';
    }
  };

  const handleDragOver = (e, item) => {
    e.preventDefault();
    if (draggedItem && item.type === 'folder') {
      e.dataTransfer.dropEffect = 'move';
      setDropTarget(item.path);
    } else if (draggedItem && !item.type) {
      // Root level drop
      e.dataTransfer.dropEffect = 'move';
      setDropTarget('__root__');
    }
  };

  const handleDragLeave = (e) => {
    setDropTarget(null);
  };

  const handleDrop = async (e, targetItem) => {
    e.preventDefault();
    e.stopPropagation();

    if (!draggedItem || draggedItem.type !== 'recipe') {
      setDraggedItem(null);
      setDropTarget(null);
      return;
    }

    const recipe = draggedItem.data;
    let newCategoryPath;

    if (targetItem && targetItem.type === 'folder') {
      newCategoryPath = targetItem.path;
    } else {
      // Dropped on root
      newCategoryPath = null;
    }

    // Don't update if dropping in same folder
    if (newCategoryPath === recipe.category_path) {
      setDraggedItem(null);
      setDropTarget(null);
      return;
    }

    try {
      await axios.patch(`${API_URL}/recipes/${recipe.id}`, {
        category_path: newCategoryPath
      });

      // Refresh recipes
      fetchRecipes();

      // Re-select the recipe if it was selected
      if (selectedRecipe?.id === recipe.id) {
        selectRecipe(recipe.id);
      }
    } catch (error) {
      console.error('Error moving recipe:', error);
      alert('Failed to move recipe');
    }

    setDraggedItem(null);
    setDropTarget(null);
  };

  return (
    <>
      <Navigation />
      <div className="recipes-container">
        <div className="recipes-layout">
        {/* Left Panel - Explorer Tree */}
        <div className="recipes-explorer">
          <div className="explorer-header">
            <h2>Recipes</h2>
            <div className="explorer-actions">
              <button onClick={createNewFolder} className="btn-new-folder" title="Create New Folder">
                📁+
              </button>
              <button onClick={createNewRecipe} className="btn-new-recipe" title="Create New Recipe">
                📄+
              </button>
              <button
                onClick={handleUploadDocument}
                className="btn-upload-recipe"
                title="Upload Recipe Document (AI-powered)"
                disabled={!currentOutlet || currentOutlet.id === 'all'}
              >
                📤
              </button>
            </div>
          </div>

          {loading ? (
            <div className="explorer-loading">Loading recipes...</div>
          ) : recipes.length === 0 ? (
            <div className="explorer-empty">
              <p>No recipes yet</p>
              <button onClick={createNewRecipe} className="btn-create-first">
                Create Your First Recipe
              </button>
            </div>
          ) : (
            <div
              className="recipe-tree"
              onDragOver={(e) => handleDragOver(e, null)}
              onDrop={(e) => handleDrop(e, null)}
            >
              {buildTree().map((node, idx) => (
                <TreeNode
                  key={node.type === 'folder' ? node.path : node.data.id}
                  node={node}
                  selectedRecipe={selectedRecipe}
                  expandedFolders={expandedFolders}
                  onToggleFolder={toggleFolder}
                  onSelectRecipe={selectRecipe}
                  onContextMenu={handleContextMenu}
                  onDragStart={handleDragStart}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  dropTarget={dropTarget}
                  depth={0}
                />
              ))}
            </div>
          )}

          {/* Context Menu */}
          {contextMenu && (
            <ContextMenu
              x={contextMenu.x}
              y={contextMenu.y}
              item={contextMenu.item}
              onRenameFolder={handleRenameFolder}
              onDeleteFolder={handleDeleteFolder}
              onClose={closeContextMenu}
            />
          )}
        </div>

        {/* Right Panel - Recipe Detail/Editor */}
        <div className="recipe-detail">
          {!selectedRecipe ? (
            <div className="detail-empty-state">
              <div className="empty-state-content">
                <h3>Welcome to Recipes</h3>
                <p>Select a recipe from the explorer to view and edit it</p>
                <p className="empty-state-stats">
                  {recipes.length} recipe{recipes.length !== 1 ? 's' : ''} total
                </p>
              </div>
            </div>
          ) : (
            <div className="recipe-editor">
              {/* Recipe Header */}
              <RecipeHeader
                recipe={selectedRecipe}
                editedRecipe={editedRecipe}
                onFieldChange={handleFieldChange}
                onDelete={handleDeleteRecipe}
              />

              {/* Recipe Metadata */}
              <RecipeMetadata
                recipe={selectedRecipe}
                editedRecipe={editedRecipe}
                onFieldChange={handleFieldChange}
              />

              {/* Ingredients Section */}
              <RecipeIngredients
                recipe={selectedRecipe}
                onIngredientsChange={() => selectRecipe(selectedRecipe.id)}
              />

              {/* Method Steps */}
              <RecipeMethod
                recipe={selectedRecipe}
                onMethodChange={() => selectRecipe(selectedRecipe.id)}
              />

              {/* Cost Panel */}
              <RecipeCost recipe={selectedRecipe} />

              {/* Notes */}
              <RecipeNotes recipe={selectedRecipe} />

              {/* Action Buttons */}
              <div className="recipe-actions">
                <button
                  className="btn-save"
                  onClick={handleUpdateRecipe}
                  disabled={!isDirty}
                >
                  Save
                </button>
                <button className="btn-cancel" onClick={handleCancel}>
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Recipe Modal */}
      {showCreateModal && (
        <RecipeCreateModal
          onClose={() => {
            setShowCreateModal(false);
            setPrefilledCategoryPath('');
          }}
          onCreate={handleCreateRecipe}
          initialCategoryPath={prefilledCategoryPath}
        />
      )}

      {/* Create Folder Modal */}
      {showFolderModal && (
        <FolderCreateModal
          onClose={() => setShowFolderModal(false)}
          onCreate={handleCreateFolder}
        />
      )}

      {/* Upload Recipe Modal */}
      {showUploadModal && (
        <UploadRecipeModal
          isOpen={showUploadModal}
          onClose={() => setShowUploadModal(false)}
          outletId={currentOutlet?.id}
          onParseComplete={handleParseComplete}
        />
      )}

      {/* Review Parsed Recipe Modal */}
      {showReviewModal && parseResult && (
        <ReviewParsedRecipe
          parseResult={parseResult}
          outletId={currentOutlet?.id}
          onClose={handleReviewClose}
        />
      )}
      </div>
    </>
  );
}

// Component Implementations

function RecipeHeader({ recipe, editedRecipe, onFieldChange, onDelete }) {
  const currentName = editedRecipe?.name !== undefined ? editedRecipe.name : recipe.name;
  const currentPath = editedRecipe?.category_path !== undefined ? editedRecipe.category_path : recipe.category_path;

  return (
    <div className="recipe-header">
      <div className="recipe-title-section">
        <input
          type="text"
          className="recipe-title-input"
          value={currentName}
          onChange={(e) => onFieldChange('name', e.target.value)}
          placeholder="Recipe Name"
        />
        <div className="recipe-header-actions">
          <button
            className="btn-icon"
            title="Delete"
            onClick={() => onDelete(recipe.id)}
          >
            🗑️
          </button>
        </div>
      </div>
      <input
        type="text"
        className="recipe-path-input"
        value={currentPath || ''}
        onChange={(e) => onFieldChange('category_path', e.target.value)}
        placeholder="Category Path (e.g., Breakfast/Hot Items)"
      />
    </div>
  );
}

function RecipeMetadata({ recipe, editedRecipe, onFieldChange }) {
  const [units, setUnits] = useState([]);

  useEffect(() => {
    fetchUnits();
  }, []);

  const fetchUnits = async () => {
    try {
      const response = await axios.get(`${API_URL}/units`);
      setUnits(response.data);
    } catch (error) {
      console.error('Error fetching units:', error);
    }
  };

  const currentYield = editedRecipe?.yield_amount !== undefined ? editedRecipe.yield_amount : recipe.yield_amount;
  const currentYieldUnit = editedRecipe?.yield_unit_id !== undefined ? editedRecipe.yield_unit_id : recipe.yield_unit_id;
  const currentServings = editedRecipe?.servings !== undefined ? editedRecipe.servings : recipe.servings;
  const currentServingUnit = editedRecipe?.serving_unit_id !== undefined ? editedRecipe.serving_unit_id : recipe.serving_unit_id;
  const currentDescription = editedRecipe?.description !== undefined ? editedRecipe.description : recipe.description;

  // Filter to common yield units (case-insensitive)
  const yieldUnits = units.filter(u =>
    ['ea', 'ct', 'doz', 'lb', 'oz', 'kg', 'g', 'gal', 'qt', 'pt', 'cup', 'l', 'ml'].includes(u.abbreviation.toLowerCase())
  );

  // Serving units - portions (null) plus weight/volume units for serving sizes (case-insensitive)
  const servingUnits = units.filter(u =>
    ['oz', 'g', 'cup', 'ml', 'fl oz'].includes(u.abbreviation.toLowerCase())
  );

  return (
    <div className="recipe-metadata">
      <div className="metadata-row">
        <div className="metadata-field yield-field">
          <label>Yield:</label>
          <input
            type="number"
            className="metadata-input"
            value={currentYield || ''}
            onChange={(e) => onFieldChange('yield_amount', parseFloat(e.target.value) || null)}
            placeholder="2"
            step="0.1"
          />
          <select
            className="metadata-select"
            value={currentYieldUnit !== null && currentYieldUnit !== undefined ? String(currentYieldUnit) : ''}
            onChange={(e) => onFieldChange('yield_unit_id', e.target.value ? parseInt(e.target.value) : null)}
          >
            <option value="">(select unit)</option>
            <optgroup label="Count">
              {yieldUnits.filter(u => ['ea', 'ct', 'doz'].includes(u.abbreviation.toLowerCase())).map(unit => (
                <option key={unit.id} value={unit.id}>{unit.name} ({unit.abbreviation})</option>
              ))}
            </optgroup>
            <optgroup label="Weight">
              {yieldUnits.filter(u => ['lb', 'oz', 'kg', 'g'].includes(u.abbreviation.toLowerCase())).map(unit => (
                <option key={unit.id} value={unit.id}>{unit.name} ({unit.abbreviation})</option>
              ))}
            </optgroup>
            <optgroup label="Volume">
              {yieldUnits.filter(u => ['gal', 'qt', 'pt', 'cup', 'l', 'ml'].includes(u.abbreviation.toLowerCase())).map(unit => (
                <option key={unit.id} value={unit.id}>{unit.name} ({unit.abbreviation})</option>
              ))}
            </optgroup>
          </select>
        </div>
        <div className="metadata-field servings-field">
          <label>Servings:</label>
          <input
            type="number"
            className="metadata-input"
            value={currentServings || ''}
            onChange={(e) => onFieldChange('servings', parseFloat(e.target.value) || null)}
            placeholder="8"
            step={currentServingUnit ? "0.1" : "1"}
            min="0.1"
          />
          <select
            className="metadata-select"
            value={currentServingUnit !== null && currentServingUnit !== undefined ? String(currentServingUnit) : ''}
            onChange={(e) => onFieldChange('serving_unit_id', e.target.value ? parseInt(e.target.value) : null)}
          >
            <option value="">portions</option>
            <optgroup label="Serving Size">
              {servingUnits.map(unit => (
                <option key={unit.id} value={unit.id}>{unit.name} ({unit.abbreviation})</option>
              ))}
            </optgroup>
          </select>
        </div>
      </div>
      <div className="metadata-field full-width">
        <label>Description:</label>
        <input
          type="text"
          className="metadata-input-full"
          value={currentDescription || ''}
          onChange={(e) => onFieldChange('description', e.target.value)}
          placeholder="Brief description of the recipe"
        />
      </div>
    </div>
  );
}

function IngredientMappingCell({ values, onFieldChange, commonProducts, onKeyDown }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredProducts, setFilteredProducts] = useState([]);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef(null);

  // Update search term when editing a mapped product
  useEffect(() => {
    if (values.common_product_id && values.common_name) {
      setSearchTerm(values.common_name);
    } else if (values.ingredient_name) {
      setSearchTerm(values.ingredient_name);
    } else {
      setSearchTerm('');
    }
  }, [values.common_product_id, values.common_name, values.ingredient_name]);

  const handleSearchChange = (term) => {
    setSearchTerm(term);
    setSelectedIndex(-1);

    // Clear current mapping and set as text-only while typing
    onFieldChange('ingredient_name', term);
    onFieldChange('common_product_id', null);
    onFieldChange('common_name', null);

    // Filter products
    if (term.length >= 2) {
      const filtered = commonProducts.filter(cp =>
        cp.common_name.toLowerCase().includes(term.toLowerCase())
      );
      setFilteredProducts(filtered);
    } else {
      setFilteredProducts([]);
    }
  };

  const handleSelectProduct = (product) => {
    onFieldChange('common_product_id', product.id);
    onFieldChange('common_name', product.common_name);
    onFieldChange('ingredient_name', null);
    setSearchTerm(product.common_name);
    setFilteredProducts([]);
    setSelectedIndex(-1);
  };

  const handleKeyDown = (e) => {
    // Arrow key navigation in dropdown
    if (filteredProducts.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev =>
          prev < filteredProducts.length - 1 ? prev + 1 : prev
        );
        return;
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
        return;
      } else if (e.key === 'Enter' && selectedIndex >= 0) {
        e.preventDefault();
        handleSelectProduct(filteredProducts[selectedIndex]);
        return;
      }
    }

    // Pass through to parent for Tab/Enter/Escape handling
    if (onKeyDown) {
      onKeyDown(e);
    }
  };

  return (
    <div className="ingredient-mapping-wrapper" onClick={e => e.stopPropagation()}>
      <input
        ref={inputRef}
        type="text"
        className="inline-edit-input"
        value={searchTerm}
        onChange={(e) => handleSearchChange(e.target.value)}
        onKeyDown={handleKeyDown}
        onFocus={(e) => e.target.select()}
        placeholder="Type to search or add text-only..."
        autoFocus
      />

      {/* Autocomplete dropdown */}
      {filteredProducts.length > 0 && (
        <div className="product-search-dropdown">
          {filteredProducts.slice(0, 10).map((p, idx) => (
            <div
              key={p.id}
              className={`product-search-item ${idx === selectedIndex ? 'selected' : ''}`}
              onClick={() => handleSelectProduct(p)}
              onMouseEnter={() => setSelectedIndex(idx)}
            >
              {p.common_name}
              {p.category && <span style={{ color: '#6b7280', marginLeft: '0.5rem' }}>({p.category})</span>}
            </div>
          ))}
        </div>
      )}

      {/* Show mapped indicator */}
      {values.common_product_id && (
        <span className="mapped-indicator" title="Mapped to product">✓</span>
      )}
    </div>
  );
}

function RecipeIngredients({ recipe, onIngredientsChange }) {
  const [commonProducts, setCommonProducts] = useState([]);
  const [availableRecipes, setAvailableRecipes] = useState([]);
  const [units, setUnits] = useState([]);
  const [showAddRow, setShowAddRow] = useState(false);
  const [addMode, setAddMode] = useState('map'); // 'map', 'text', or 'subrecipe'
  const [newIngredient, setNewIngredient] = useState({
    common_product_id: '',
    sub_recipe_id: '',
    ingredient_name: '',
    quantity: '',
    unit_id: '',
    yield_percentage: 100
  });
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredProducts, setFilteredProducts] = useState([]);
  const [filteredRecipes, setFilteredRecipes] = useState([]);
  const [showAutocomplete, setShowAutocomplete] = useState(false);
  const [editingIngredientId, setEditingIngredientId] = useState(null);
  const [editedValues, setEditedValues] = useState({});

  useEffect(() => {
    fetchCommonProducts();
    fetchUnits();
    fetchAvailableRecipes();
  }, []);

  const fetchCommonProducts = async () => {
    try {
      const response = await axios.get(`${API_URL}/common-products?limit=10000`);
      setCommonProducts(response.data);
    } catch (error) {
      console.error('Error fetching common products:', error);
    }
  };

  const fetchAvailableRecipes = async () => {
    try {
      const response = await axios.get(`${API_URL}/recipes`);
      // Filter out the current recipe to prevent circular references
      const otherRecipes = response.data.filter(r => r.id !== recipe.id);
      setAvailableRecipes(otherRecipes);
    } catch (error) {
      console.error('Error fetching recipes:', error);
    }
  };

  const fetchUnits = async () => {
    try {
      const response = await axios.get(`${API_URL}/units`);
      setUnits(response.data);
    } catch (error) {
      console.error('Error fetching units:', error);
    }
  };

  const handleSearchChange = (value) => {
    setSearchTerm(value);
    if (value.trim()) {
      if (addMode === 'subrecipe') {
        const filtered = availableRecipes.filter(r =>
          r.name.toLowerCase().includes(value.toLowerCase())
        );
        setFilteredRecipes(filtered);
      } else {
        const filtered = commonProducts.filter(cp =>
          cp.common_name.toLowerCase().includes(value.toLowerCase())
        );
        setFilteredProducts(filtered);
      }
      setShowAutocomplete(true);
    } else {
      setFilteredProducts([]);
      setFilteredRecipes([]);
      setShowAutocomplete(false);
    }
  };

  const selectProduct = (product) => {
    setNewIngredient({ ...newIngredient, common_product_id: product.id, sub_recipe_id: '' });
    setSearchTerm(product.common_name);
    setShowAutocomplete(false);
  };

  const selectSubRecipe = (subRecipe) => {
    setNewIngredient({ ...newIngredient, sub_recipe_id: subRecipe.id, common_product_id: '' });
    setSearchTerm(subRecipe.name);
    setShowAutocomplete(false);
  };

  const handleAddIngredient = async () => {
    // Validate based on mode
    if (addMode === 'map') {
      if (!newIngredient.common_product_id || !newIngredient.quantity || !newIngredient.unit_id) {
        alert('Please fill in all required fields');
        return;
      }
    } else if (addMode === 'subrecipe') {
      if (!newIngredient.sub_recipe_id || !newIngredient.quantity || !newIngredient.unit_id) {
        alert('Please fill in all required fields');
        return;
      }
    } else {
      if (!newIngredient.ingredient_name || !newIngredient.quantity || !newIngredient.unit_id) {
        alert('Please fill in all required fields');
        return;
      }
    }

    try {
      let ingredientData;
      if (addMode === 'map') {
        ingredientData = {
          common_product_id: parseInt(newIngredient.common_product_id),
          quantity: parseFloat(newIngredient.quantity),
          unit_id: parseInt(newIngredient.unit_id),
          yield_percentage: parseFloat(newIngredient.yield_percentage)
        };
      } else if (addMode === 'subrecipe') {
        ingredientData = {
          sub_recipe_id: parseInt(newIngredient.sub_recipe_id),
          quantity: parseFloat(newIngredient.quantity),
          unit_id: parseInt(newIngredient.unit_id),
          yield_percentage: parseFloat(newIngredient.yield_percentage)
        };
      } else {
        ingredientData = {
          ingredient_name: newIngredient.ingredient_name,
          quantity: parseFloat(newIngredient.quantity),
          unit_id: parseInt(newIngredient.unit_id),
          yield_percentage: parseFloat(newIngredient.yield_percentage)
        };
      }

      await axios.post(`${API_URL}/recipes/${recipe.id}/ingredients`, ingredientData);

      // Refresh recipe to get updated ingredients
      onIngredientsChange();

      // Reset form
      setNewIngredient({
        common_product_id: '',
        sub_recipe_id: '',
        ingredient_name: '',
        quantity: '',
        unit_id: '',
        yield_percentage: 100
      });
      setSearchTerm('');
      setShowAddRow(false);
    } catch (error) {
      console.error('Error adding ingredient:', error);
      alert('Failed to add ingredient');
    }
  };

  const handleRemoveIngredient = async (ingredientId) => {
    if (!confirm('Remove this ingredient?')) return;

    try {
      await axios.delete(`${API_URL}/recipes/${recipe.id}/ingredients/${ingredientId}`);
      onIngredientsChange();
    } catch (error) {
      console.error('Error removing ingredient:', error);
      alert('Failed to remove ingredient');
    }
  };

  const handleStartEdit = (ingredientId) => {
    const ingredient = recipe.ingredients.find(i => i.id === ingredientId);
    setEditingIngredientId(ingredientId);
    setEditedValues({
      id: ingredient.id,
      common_product_id: ingredient.common_product_id,
      ingredient_name: ingredient.ingredient_name,
      common_name: ingredient.common_name,
      quantity: ingredient.quantity,
      unit_id: ingredient.unit_id,
      yield_percentage: ingredient.yield_percentage
    });
  };

  const handleFieldChange = (field, value) => {
    setEditedValues(prev => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    // Validation
    if (!editedValues.quantity || parseFloat(editedValues.quantity) <= 0) {
      alert('Quantity must be greater than 0');
      return;
    }

    if (!editedValues.unit_id) {
      alert('Unit is required');
      return;
    }

    if (!editedValues.common_product_id && !editedValues.ingredient_name) {
      alert('Ingredient must be mapped to a product or have a name');
      return;
    }

    try {
      const updates = {
        quantity: parseFloat(editedValues.quantity),
        unit_id: parseInt(editedValues.unit_id),
        yield_percentage: parseFloat(editedValues.yield_percentage)
      };

      // Include mapping changes
      if (editedValues.common_product_id !== undefined) {
        updates.common_product_id = editedValues.common_product_id;
      }
      if (editedValues.ingredient_name !== undefined) {
        updates.ingredient_name = editedValues.ingredient_name;
      }

      await axios.patch(
        `${API_URL}/recipes/${recipe.id}/ingredients/${editedValues.id}`,
        updates
      );

      onIngredientsChange(); // Refresh data
      setEditingIngredientId(null);
      setEditedValues({});
    } catch (error) {
      console.error('Error updating ingredient:', error);
      alert(error.response?.data?.detail || 'Failed to update ingredient');
    }
  };

  const handleCancel = () => {
    setEditingIngredientId(null);
    setEditedValues({});
  };

  const handleKeyDown = (e, field) => {
    // Escape - cancel editing
    if (e.key === 'Escape') {
      e.preventDefault();
      handleCancel();
      return;
    }

    // Enter - save and move to next row (Excel-like behavior)
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSave().then(() => {
        const currentIndex = recipe.ingredients.findIndex(i => i.id === editingIngredientId);
        const nextIngredient = recipe.ingredients[currentIndex + 1];
        if (nextIngredient) {
          setTimeout(() => handleStartEdit(nextIngredient.id), 100);
        }
      }).catch(() => {
        // Save failed, stay in edit mode
      });
      return;
    }

    // Tab - move to next field (Excel-like behavior)
    if (e.key === 'Tab') {
      e.preventDefault();
      const fields = ['ingredient', 'quantity', 'unit', 'yield'];
      const currentIdx = fields.indexOf(field);
      const nextIdx = e.shiftKey ? currentIdx - 1 : currentIdx + 1;

      if (nextIdx >= 0 && nextIdx < fields.length) {
        // Move to next/previous field in same row
        const nextField = fields[nextIdx];
        const selector = `.editing [data-field="${nextField}"]`;
        const nextInput = document.querySelector(selector);
        if (nextInput) {
          nextInput.focus();
          if (nextInput.select) nextInput.select();
        }
      } else if (!e.shiftKey && nextIdx >= fields.length) {
        // Reached end of row, save and move to next row
        const currentIndex = recipe.ingredients.findIndex(i => i.id === editingIngredientId);
        const nextIngredient = recipe.ingredients[currentIndex + 1];
        if (nextIngredient) {
          handleSave().then(() => {
            setTimeout(() => handleStartEdit(nextIngredient.id), 100);
          }).catch(() => {
            // Save failed, stay in edit mode
          });
        }
      }
    }
  };

  return (
    <div className="recipe-section">
      <h2>Ingredients</h2>
      <div className="ingredients-table-container">
        <table className="ingredients-table">
          <thead>
            <tr>
              <th style={{ width: '60px', textAlign: 'center' }}>Mapped?</th>
              <th>Ingredient</th>
              <th>Quantity</th>
              <th>Unit</th>
              <th>Yield %</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {recipe.ingredients && recipe.ingredients.length > 0 ? (
              recipe.ingredients.map((ing) => {
                const isEditing = editingIngredientId === ing.id;
                const values = isEditing ? editedValues : ing;

                return (
                  <tr key={ing.id} className={isEditing ? 'editing' : ''}>
                    {/* Mapped Indicator Column */}
                    <td className="mapped-cell">
                      {values.common_product_id ?
                        <span className="mapped-yes">✓</span> :
                        <span className="mapped-no">×</span>
                      }
                    </td>

                    {/* Ingredient Name/Mapping Column */}
                    <td>
                      {isEditing ? (
                        <div data-field="ingredient">
                          <IngredientMappingCell
                            values={values}
                            onFieldChange={handleFieldChange}
                            commonProducts={commonProducts}
                            onKeyDown={(e) => handleKeyDown(e, 'ingredient')}
                          />
                        </div>
                      ) : (
                        <span onClick={() => handleStartEdit(ing.id)}>
                          {ing.ingredient_name || ing.common_name || ing.sub_recipe_name || 'Unknown'}
                          {ing.sub_recipe_id && <span className="sub-recipe-badge">sub-recipe</span>}
                        </span>
                      )}
                    </td>

                    {/* Quantity Column */}
                    <td>
                      {isEditing ? (
                        <input
                          type="number"
                          className="inline-edit-input"
                          data-field="quantity"
                          value={values.quantity}
                          onChange={(e) => handleFieldChange('quantity', e.target.value)}
                          onKeyDown={(e) => handleKeyDown(e, 'quantity')}
                          onFocus={(e) => e.target.select()}
                          step="0.01"
                        />
                      ) : (
                        <span onClick={() => handleStartEdit(ing.id)}>{ing.quantity}</span>
                      )}
                    </td>

                    {/* Unit Column */}
                    <td>
                      {isEditing ? (
                        <select
                          className="inline-edit-select"
                          data-field="unit"
                          value={values.unit_id}
                          onChange={(e) => handleFieldChange('unit_id', e.target.value)}
                          onKeyDown={(e) => handleKeyDown(e, 'unit')}
                        >
                          {units.map(u => (
                            <option key={u.id} value={u.id}>{u.abbreviation}</option>
                          ))}
                        </select>
                      ) : (
                        <span onClick={() => handleStartEdit(ing.id)}>{ing.unit_abbreviation}</span>
                      )}
                    </td>

                    {/* Yield % Column */}
                    <td>
                      {isEditing ? (
                        <input
                          type="number"
                          className="inline-edit-input"
                          data-field="yield"
                          value={values.yield_percentage}
                          onChange={(e) => handleFieldChange('yield_percentage', e.target.value)}
                          onKeyDown={(e) => handleKeyDown(e, 'yield')}
                          onFocus={(e) => e.target.select()}
                          min="0"
                          max="100"
                          step="1"
                        />
                      ) : (
                        <span onClick={() => handleStartEdit(ing.id)}>{ing.yield_percentage}%</span>
                      )}
                    </td>

                    {/* Actions Column */}
                    <td>
                      {isEditing ? (
                        <>
                          <button className="btn-icon-small" onClick={handleSave} title="Save">✓</button>
                          <button className="btn-icon-small" onClick={handleCancel} title="Cancel">×</button>
                        </>
                      ) : (
                        <button
                          className="btn-icon-small"
                          onClick={() => handleRemoveIngredient(ing.id)}
                          title="Delete"
                        >
                          ×
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })
            ) : (
              <tr>
                <td colSpan="6" className="empty-cell">No ingredients yet</td>
              </tr>
            )}
            {showAddRow && (
              <tr className="ingredient-add-row">
                <td colSpan="6">
                  <div style={{ marginBottom: '0.75rem' }}>
                    <div className="add-mode-toggle" style={{ display: 'inline-flex', gap: 0, border: '1px solid #d1d5db', borderRadius: '6px', overflow: 'hidden' }}>
                      <button
                        type="button"
                        style={{
                          padding: '0.5rem 1rem',
                          background: addMode === 'map' ? '#3b82f6' : '#fff',
                          color: addMode === 'map' ? 'white' : '#6b7280',
                          border: 'none',
                          fontWeight: '500',
                          cursor: 'pointer'
                        }}
                        onClick={() => { setAddMode('map'); setSearchTerm(''); setShowAutocomplete(false); }}
                      >
                        Map to Product
                      </button>
                      <button
                        type="button"
                        style={{
                          padding: '0.5rem 1rem',
                          background: addMode === 'subrecipe' ? '#3b82f6' : '#fff',
                          color: addMode === 'subrecipe' ? 'white' : '#6b7280',
                          border: 'none',
                          fontWeight: '500',
                          cursor: 'pointer'
                        }}
                        onClick={() => { setAddMode('subrecipe'); setSearchTerm(''); setShowAutocomplete(false); }}
                      >
                        Sub-Recipe
                      </button>
                      <button
                        type="button"
                        style={{
                          padding: '0.5rem 1rem',
                          background: addMode === 'text' ? '#3b82f6' : '#fff',
                          color: addMode === 'text' ? 'white' : '#6b7280',
                          border: 'none',
                          fontWeight: '500',
                          cursor: 'pointer'
                        }}
                        onClick={() => { setAddMode('text'); setSearchTerm(''); setShowAutocomplete(false); }}
                      >
                        Quick Add Text
                      </button>
                    </div>
                  </div>

                  {addMode === 'map' ? (
                    <div className="autocomplete-container">
                      <input
                        type="text"
                        className="ingredient-input"
                        value={searchTerm}
                        onChange={(e) => handleSearchChange(e.target.value)}
                        placeholder="Search common products..."
                        autoFocus
                        style={{ width: '100%', marginBottom: '0.5rem' }}
                      />
                      {showAutocomplete && filteredProducts.length > 0 && (
                        <div className="autocomplete-dropdown">
                          {filteredProducts.slice(0, 10).map(product => (
                            <div
                              key={product.id}
                              className="autocomplete-item"
                              onClick={() => selectProduct(product)}
                            >
                              {product.common_name}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ) : addMode === 'subrecipe' ? (
                    <div className="autocomplete-container">
                      <input
                        type="text"
                        className="ingredient-input"
                        value={searchTerm}
                        onChange={(e) => handleSearchChange(e.target.value)}
                        placeholder="Search recipes..."
                        autoFocus
                        style={{ width: '100%', marginBottom: '0.5rem' }}
                      />
                      {showAutocomplete && filteredRecipes.length > 0 && (
                        <div className="autocomplete-dropdown">
                          {filteredRecipes.slice(0, 10).map(r => (
                            <div
                              key={r.id}
                              className="autocomplete-item"
                              onClick={() => selectSubRecipe(r)}
                            >
                              {r.name}
                              {r.category && <span style={{ marginLeft: '0.5rem', color: '#9ca3af', fontSize: '0.8em' }}>{r.category}</span>}
                            </div>
                          ))}
                        </div>
                      )}
                      <small style={{ display: 'block', marginTop: '0.25rem', color: '#6b7280', fontSize: '0.75rem' }}>
                        Sub-recipe costs will be calculated from their ingredients
                      </small>
                    </div>
                  ) : (
                    <div style={{ marginBottom: '0.5rem' }}>
                      <input
                        type="text"
                        className="ingredient-input"
                        value={newIngredient.ingredient_name}
                        onChange={(e) => setNewIngredient({ ...newIngredient, ingredient_name: e.target.value })}
                        placeholder="Ingredient name (e.g., 'Fresh basil, chopped')"
                        autoFocus
                        style={{ width: '100%' }}
                      />
                      <small style={{ display: 'block', marginTop: '0.25rem', color: '#6b7280', fontSize: '0.75rem' }}>
                        Text-only ingredients won't have cost tracking
                      </small>
                    </div>
                  )}

                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: '0.5rem' }}>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>Quantity</label>
                      <input
                        type="number"
                        className="ingredient-input"
                        value={newIngredient.quantity}
                        onChange={(e) => setNewIngredient({ ...newIngredient, quantity: e.target.value })}
                        placeholder="0"
                        step="0.01"
                        style={{ width: '100%' }}
                      />
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>Unit</label>
                      <select
                        className="ingredient-input"
                        value={newIngredient.unit_id}
                        onChange={(e) => setNewIngredient({ ...newIngredient, unit_id: e.target.value })}
                        style={{ width: '100%' }}
                      >
                        <option value="">Select unit</option>
                        {units.map(unit => (
                          <option key={unit.id} value={unit.id}>
                            {unit.abbreviation}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.75rem', color: '#6b7280', marginBottom: '0.25rem' }}>Yield %</label>
                      <input
                        type="number"
                        className="ingredient-input"
                        value={newIngredient.yield_percentage}
                        onChange={(e) => setNewIngredient({ ...newIngredient, yield_percentage: e.target.value })}
                        step="1"
                        min="0"
                        max="100"
                        style={{ width: '100%' }}
                      />
                    </div>
                    <div style={{ display: 'flex', gap: '0.25rem', alignSelf: 'end' }}>
                      <button
                        className="btn-icon-small btn-save-ingredient"
                        onClick={handleAddIngredient}
                        title="Save ingredient"
                      >
                        ✓
                      </button>
                      <button
                        className="btn-icon-small"
                        onClick={() => {
                          setShowAddRow(false);
                          setSearchTerm('');
                          setNewIngredient({
                            common_product_id: '',
                            sub_recipe_id: '',
                            ingredient_name: '',
                            quantity: '',
                            unit_id: '',
                            yield_percentage: 100
                          });
                        }}
                        title="Cancel"
                      >
                        ×
                      </button>
                    </div>
                  </div>
                </td>
              </tr>
            )}
          </tbody>
        </table>
        <button
          className="btn-add-ingredient"
          onClick={() => setShowAddRow(true)}
          disabled={showAddRow}
        >
          + Add Ingredient
        </button>
      </div>
    </div>
  );
}

function RecipeMethod({ recipe, onMethodChange }) {
  const [steps, setSteps] = useState(recipe.method || []);
  const [editingStepIndex, setEditingStepIndex] = useState(null);

  useEffect(() => {
    setSteps(recipe.method || []);
  }, [recipe.method]);

  const handleAddStep = () => {
    const newStep = {
      step_number: steps.length + 1,
      instruction: ''
    };
    setSteps([...steps, newStep]);
    setEditingStepIndex(steps.length);
  };

  const handleStepChange = (index, instruction) => {
    const updatedSteps = [...steps];
    updatedSteps[index].instruction = instruction;
    setSteps(updatedSteps);
  };

  const handleRemoveStep = (index) => {
    if (!confirm('Remove this step?')) return;

    const updatedSteps = steps.filter((_, i) => i !== index);
    // Renumber steps
    updatedSteps.forEach((step, i) => {
      step.step_number = i + 1;
    });
    setSteps(updatedSteps);
    saveMethod(updatedSteps);
  };

  const handleMoveStep = (index, direction) => {
    if (
      (direction === 'up' && index === 0) ||
      (direction === 'down' && index === steps.length - 1)
    ) {
      return;
    }

    const newIndex = direction === 'up' ? index - 1 : index + 1;
    const updatedSteps = [...steps];
    [updatedSteps[index], updatedSteps[newIndex]] = [updatedSteps[newIndex], updatedSteps[index]];

    // Renumber steps
    updatedSteps.forEach((step, i) => {
      step.step_number = i + 1;
    });

    setSteps(updatedSteps);
    saveMethod(updatedSteps);
  };

  const saveMethod = async (updatedSteps) => {
    try {
      await axios.patch(`${API_URL}/recipes/${recipe.id}`, {
        method: updatedSteps
      });
      onMethodChange();
    } catch (error) {
      console.error('Error updating method:', error);
      alert('Failed to update method');
    }
  };

  const handleSaveStep = (index) => {
    if (!steps[index].instruction.trim()) {
      alert('Step instruction cannot be empty');
      return;
    }
    setEditingStepIndex(null);
    saveMethod(steps);
  };

  return (
    <div className="recipe-section">
      <h2>Method</h2>
      <div className="method-steps">
        {steps.length > 0 ? (
          steps.map((step, idx) => (
            <div key={idx} className="method-step">
              <div className="step-header">
                <div className="step-number">{step.step_number}</div>
                <div className="step-controls">
                  <button
                    className="btn-step-control"
                    onClick={() => handleMoveStep(idx, 'up')}
                    disabled={idx === 0}
                    title="Move up"
                  >
                    ↑
                  </button>
                  <button
                    className="btn-step-control"
                    onClick={() => handleMoveStep(idx, 'down')}
                    disabled={idx === steps.length - 1}
                    title="Move down"
                  >
                    ↓
                  </button>
                  <button
                    className="btn-step-control btn-remove"
                    onClick={() => handleRemoveStep(idx)}
                    title="Remove step"
                  >
                    ×
                  </button>
                </div>
              </div>
              {editingStepIndex === idx ? (
                <div className="step-edit-container">
                  <textarea
                    className="step-instruction-input"
                    value={step.instruction}
                    onChange={(e) => handleStepChange(idx, e.target.value)}
                    placeholder="Enter step instruction..."
                    autoFocus
                    rows="3"
                  />
                  <div className="step-edit-actions">
                    <button
                      className="btn-step-save"
                      onClick={() => handleSaveStep(idx)}
                    >
                      Save
                    </button>
                    <button
                      className="btn-step-cancel"
                      onClick={() => {
                        setEditingStepIndex(null);
                        setSteps(recipe.method || []);
                      }}
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <div
                  className="step-instruction"
                  onClick={() => setEditingStepIndex(idx)}
                  title="Click to edit"
                >
                  {step.instruction || <span className="placeholder-text">Click to add instruction...</span>}
                </div>
              )}
            </div>
          ))
        ) : (
          <div className="empty-method">No method steps yet</div>
        )}
        <button className="btn-add-step" onClick={handleAddStep}>
          + Add Step
        </button>
      </div>
    </div>
  );
}

function RecipeCost({ recipe }) {
  const [costData, setCostData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    if (recipe?.id) {
      fetchCostData();
    }
  }, [recipe?.id, recipe?.updated_at]);

  const fetchCostData = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await axios.get(`${API_URL}/recipes/${recipe.id}/cost`);
      setCostData(response.data);
    } catch (err) {
      console.error('Error fetching cost data:', err);
      setError('Failed to calculate costs');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (value) => {
    if (value === null || value === undefined) return '-';
    return `$${value.toFixed(2)}`;
  };

  const ingredientsWithMissingPrices = costData?.ingredients?.filter(ing => !ing.has_price) || [];
  const ingredientsWithPrices = costData?.ingredients?.filter(ing => ing.has_price) || [];

  return (
    <div className="recipe-section recipe-cost-section">
      <div className="section-header-collapsible" onClick={() => setIsCollapsed(!isCollapsed)}>
        <h2>
          <span className="collapse-icon">{isCollapsed ? '▶' : '▼'}</span>
          Cost Analysis
        </h2>
        {!isCollapsed && costData && (
          <span className="cost-header-summary">
            Total: {formatCurrency(costData.total_cost)}
          </span>
        )}
      </div>

      {!isCollapsed && (
        <div className="cost-panel">
          {loading ? (
            <div className="cost-loading">Calculating costs...</div>
          ) : error ? (
            <div className="cost-error">{error}</div>
          ) : !costData ? (
            <div className="cost-empty">No cost data available</div>
          ) : (
            <>
              {/* Cost Summary */}
              <div className="cost-summary">
                <div className="cost-item cost-total">
                  <label>Total Cost:</label>
                  <span className="cost-value">{formatCurrency(costData.total_cost)}</span>
                </div>
                <div className="cost-item">
                  <label>Cost per {costData.serving_unit_abbreviation || 'Serving'}:</label>
                  <span className="cost-value">
                    {costData.cost_per_serving !== null
                      ? formatCurrency(costData.cost_per_serving)
                      : <span className="no-yield">Set servings to calculate</span>
                    }
                  </span>
                </div>
                {(costData.yield_amount || costData.servings) && (
                  <div className="cost-item cost-yield">
                    {costData.yield_amount && costData.yield_unit_abbreviation && (
                      <div>
                        <label>Yield:</label>
                        <span className="cost-value-small">
                          {costData.yield_amount} {costData.yield_unit_abbreviation}
                        </span>
                      </div>
                    )}
                    {costData.servings && (
                      <div>
                        <label>Servings:</label>
                        <span className="cost-value-small">
                          {costData.servings} {costData.serving_unit_abbreviation || 'portions'}
                        </span>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Missing Price Warning */}
              {ingredientsWithMissingPrices.length > 0 && (
                <div className="cost-warning">
                  <span className="warning-icon">⚠️</span>
                  <span>
                    {ingredientsWithMissingPrices.length} ingredient{ingredientsWithMissingPrices.length !== 1 ? 's' : ''} missing price data
                  </span>
                </div>
              )}

              {/* Cost Breakdown Table */}
              {costData.ingredients && costData.ingredients.length > 0 && (
                <div className="cost-breakdown">
                  <h3>Cost Breakdown</h3>
                  <table className="cost-breakdown-table">
                    <thead>
                      <tr>
                        <th>Ingredient</th>
                        <th>Qty</th>
                        <th>Unit Price</th>
                        <th>Cost</th>
                        <th>%</th>
                      </tr>
                    </thead>
                    <tbody>
                      {costData.ingredients.map((ing) => (
                        <tr
                          key={ing.id}
                          className={!ing.has_price ? 'missing-price' : ''}
                        >
                          <td className="ingredient-cell">
                            {ing.common_name || ing.sub_recipe_name || 'Unknown'}
                            {ing.sub_recipe_id && <span className="sub-recipe-badge">sub-recipe</span>}
                          </td>
                          <td className="qty-cell">
                            {ing.quantity} {ing.unit_abbreviation}
                          </td>
                          <td className="price-cell">
                            {ing.has_price ? (
                              <span title={ing.price_source}>
                                {ing.unit_price ? `$${ing.unit_price.toFixed(4)}` : '-'}
                              </span>
                            ) : (
                              <span className="no-price">No price</span>
                            )}
                          </td>
                          <td className="cost-cell">
                            {ing.cost !== null ? formatCurrency(ing.cost) : '-'}
                          </td>
                          <td className="percent-cell">
                            {ing.cost_percentage !== null ? `${ing.cost_percentage}%` : '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr className="total-row">
                        <td colSpan="3">Total</td>
                        <td className="cost-cell">{formatCurrency(costData.total_cost)}</td>
                        <td className="percent-cell">100%</td>
                      </tr>
                    </tfoot>
                  </table>
                </div>
              )}

              {/* Allergen Summary */}
              {costData.allergens && (
                <div className="allergen-summary">
                  <h3>Allergens & Dietary</h3>

                  {/* Dietary Flags */}
                  <div className="dietary-flags">
                    <span className={`dietary-badge ${costData.allergens.vegan ? 'active' : 'inactive'}`}>
                      🌱 {costData.allergens.vegan ? 'Vegan' : 'Not Vegan'}
                    </span>
                    <span className={`dietary-badge ${costData.allergens.vegetarian ? 'active' : 'inactive'}`}>
                      🥗 {costData.allergens.vegetarian ? 'Vegetarian' : 'Not Vegetarian'}
                    </span>
                  </div>

                  {/* Allergen List */}
                  {costData.allergens.contains.length > 0 ? (
                    <div className="allergen-contains">
                      <div className="allergen-label">Contains:</div>
                      <div className="allergen-badges">
                        {costData.allergens.contains.map(allergen => (
                          <span key={allergen} className="allergen-badge" title={allergen}>
                            {ALLERGEN_ICONS[allergen] || '⚠️'} {allergen}
                          </span>
                        ))}
                      </div>
                    </div>
                  ) : (
                    <div className="allergen-none">
                      No allergens flagged for this recipe's ingredients
                    </div>
                  )}
                </div>
              )}

              {/* Refresh Button */}
              <button className="btn-refresh-cost" onClick={fetchCostData}>
                🔄 Refresh Costs
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function RecipeNotes({ recipe }) {
  return (
    <div className="recipe-section">
      <h2>Notes</h2>
      <textarea
        className="recipe-notes-textarea"
        placeholder="Add notes about this recipe..."
        defaultValue={recipe.notes || ''}
        readOnly
      />
    </div>
  );
}

// Create Recipe Modal
function RecipeCreateModal({ onClose, onCreate, initialCategoryPath = '' }) {
  const { currentOutlet, outlets } = useOutlet();
  const [formData, setFormData] = useState({
    name: '',
    category_path: initialCategoryPath,
    description: '',
    yield_amount: '',
    outlet_id: currentOutlet?.id && currentOutlet.id !== 'all' ? currentOutlet.id : ''
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      alert('Recipe name is required');
      return;
    }

    onCreate({
      ...formData,
      yield_amount: formData.yield_amount ? parseFloat(formData.yield_amount) : null
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Create New Recipe</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-group">
            <label>Recipe Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g., Chicken Carbonara"
              required
              autoFocus
            />
          </div>

          <div className="form-group">
            <label>Category Path</label>
            <input
              type="text"
              value={formData.category_path}
              onChange={(e) => setFormData({ ...formData, category_path: e.target.value })}
              placeholder="e.g., Dinner/Italian/Pasta"
            />
            <small>Use / to create nested folders (e.g., Breakfast/Hot Items)</small>
          </div>

          <div className="form-group">
            <label>Outlet *</label>
            <select
              value={formData.outlet_id}
              onChange={(e) => setFormData({ ...formData, outlet_id: e.target.value })}
              required
            >
              <option value="">Select Outlet</option>
              {outlets.filter(o => o.id !== 'all').map(outlet => (
                <option key={outlet.id} value={outlet.id}>{outlet.name}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Description</label>
            <input
              type="text"
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Brief description"
            />
          </div>

          <div className="form-group">
            <label>Yield (portions)</label>
            <input
              type="number"
              value={formData.yield_amount}
              onChange={(e) => setFormData({ ...formData, yield_amount: e.target.value })}
              placeholder="4"
              step="0.1"
              min="0"
            />
          </div>

          <div className="modal-actions">
            <button type="button" className="btn-cancel" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-save">
              Create Recipe
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Create Folder Modal
function FolderCreateModal({ onClose, onCreate }) {
  const [folderPath, setFolderPath] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!folderPath.trim()) {
      alert('Folder path is required');
      return;
    }

    onCreate(folderPath.trim());
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Create New Folder</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>

        <form onSubmit={handleSubmit} className="modal-form">
          <div className="form-group">
            <label>Folder Path *</label>
            <input
              type="text"
              value={folderPath}
              onChange={(e) => setFolderPath(e.target.value)}
              placeholder="e.g., Breakfast/Hot Items"
              required
              autoFocus
            />
            <small>Use / to create nested folders. The folder will be created immediately and you can add recipes to it later.</small>
          </div>

          <div className="modal-actions">
            <button type="button" className="btn-cancel" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn-save">
              Create Folder
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Context Menu Component
function ContextMenu({ x, y, item, onRenameFolder, onDeleteFolder, onClose }) {
  const handleAction = (action) => {
    action();
    onClose();
  };

  return (
    <div
      className="context-menu"
      style={{ left: x, top: y }}
      onClick={(e) => e.stopPropagation()}
    >
      {item.type === 'folder' ? (
        <>
          <div
            className="context-menu-item"
            onClick={() => handleAction(() => onRenameFolder(item.path))}
          >
            ✏️ Rename Folder
          </div>
          <div
            className="context-menu-item"
            onClick={() => handleAction(() => onDeleteFolder(item.path))}
          >
            🗑️ Delete Folder
          </div>
        </>
      ) : (
        <>
          <div className="context-menu-item context-menu-disabled">
            Move to...
          </div>
          <div className="context-menu-item context-menu-disabled">
            Duplicate
          </div>
        </>
      )}
    </div>
  );
}

// Tree Node Component
function TreeNode({
  node,
  selectedRecipe,
  expandedFolders,
  onToggleFolder,
  onSelectRecipe,
  onContextMenu,
  onDragStart,
  onDragOver,
  onDragLeave,
  onDrop,
  dropTarget,
  depth
}) {
  if (node.type === 'folder') {
    const isExpanded = expandedFolders.has(node.path);
    const hasChildren = node.children && node.children.length > 0;
    const isDropTarget = dropTarget === node.path;

    return (
      <>
        <div
          className={`tree-folder ${isDropTarget ? 'drop-target' : ''}`}
          style={{ paddingLeft: `${depth * 1.5}rem` }}
          onClick={() => hasChildren && onToggleFolder(node.path)}
          onContextMenu={(e) => onContextMenu(e, node)}
          onDragOver={(e) => onDragOver(e, node)}
          onDragLeave={onDragLeave}
          onDrop={(e) => onDrop(e, node)}
        >
          <span className="folder-icon">
            {hasChildren ? (isExpanded ? '📂' : '📁') : '📁'}
          </span>
          <span className="folder-name">{node.name}</span>
          <span className="folder-count">({node.children.length})</span>
        </div>
        {isExpanded && hasChildren && (
          <>
            {node.children.map((child, idx) => (
              <TreeNode
                key={child.type === 'folder' ? child.path : child.data.id}
                node={child}
                selectedRecipe={selectedRecipe}
                expandedFolders={expandedFolders}
                onToggleFolder={onToggleFolder}
                onSelectRecipe={onSelectRecipe}
                onContextMenu={onContextMenu}
                onDragStart={onDragStart}
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
                dropTarget={dropTarget}
                depth={depth + 1}
              />
            ))}
          </>
        )}
      </>
    );
  }

  // Recipe node
  return (
    <div
      className={`recipe-item ${selectedRecipe?.id === node.data.id ? 'selected' : ''}`}
      style={{ paddingLeft: `${depth * 1.5}rem` }}
      draggable
      onClick={() => onSelectRecipe(node.data.id)}
      onContextMenu={(e) => onContextMenu(e, node)}
      onDragStart={(e) => onDragStart(e, node)}
    >
      <span className="recipe-icon">📄</span>
      <span className="recipe-name">{node.data.name}</span>
      <OutletBadge outletId={node.data.outlet_id} />
    </div>
  );
}

export default Recipes;
