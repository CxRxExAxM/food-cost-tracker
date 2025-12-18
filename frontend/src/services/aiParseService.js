/**
 * AI Parse Service - API calls for AI recipe parsing
 */

import axios from '../lib/axios';

/**
 * Parse uploaded recipe file with AI
 * @param {File} file - Recipe document (.docx, .pdf, .xlsx)
 * @param {number} outletId - Outlet ID for context
 * @returns {Promise} Parse results with ingredients and product matches
 */
export const parseRecipeFile = async (file, outletId) => {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('outlet_id', outletId);

  const response = await axios.post('/recipes/parse-file', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });

  return response.data;
};

/**
 * Create recipe from AI parse results
 * @param {object} data - Recipe data from review
 * @returns {Promise} Created recipe with ID
 */
export const createRecipeFromParse = async (data) => {
  const response = await axios.post('/recipes/create-from-parse', data);
  return response.data;
};

/**
 * Get AI parse usage statistics
 * @returns {Promise} Usage stats for current organization
 */
export const getUsageStats = async () => {
  const response = await axios.get('/ai-parse/usage-stats');
  return response.data;
};

/**
 * Quick create common product during review
 * @param {object} productData - Product details (name, category, subcategory)
 * @returns {Promise} Created product with ID
 */
export const quickCreateProduct = async (productData) => {
  const response = await axios.post('/common-products/quick-create', productData);
  return response.data;
};

/**
 * Search common products for matching
 * @param {string} searchTerm - Search query
 * @returns {Promise} Array of matching products
 */
export const searchProducts = async (searchTerm) => {
  const response = await axios.get('/common-products', {
    params: {
      search: searchTerm,
      limit: 20,
    },
  });
  return response.data;
};
