import React, { useState, useEffect } from 'react';
import { Package, Plus } from 'lucide-react';
import api from '../services/api';

function Products() {
  const [products, setProducts] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    description: '',
    category: '',
    unit_of_measure: 'Unit',
    unit_price: 0,
    cost_price: 0,
    product_type: 'storable'
  });

  useEffect(() => {
    fetchProducts();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await api.get('/api/products');
      setProducts(response.data);
    } catch (error) {
      console.error('Error fetching products:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.post('/api/products', formData);
      setShowForm(false);
      setFormData({
        code: '',
        name: '',
        description: '',
        category: '',
        unit_of_measure: 'Unit',
        unit_price: 0,
        cost_price: 0,
        product_type: 'storable'
      });
      fetchProducts();
    } catch (error) {
      console.error('Error creating product:', error);
      alert('Failed to create product');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold gradient-text">Products & Inventory</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-gradient-to-r from-erik-primary to-green-500 text-white px-6 py-2 rounded-lg font-semibold hover:shadow-lg hover:shadow-erik-primary/50 transition-all flex items-center gap-2"
        >
          <Plus size={20} />
          Add Product
        </button>
      </div>

      {showForm && (
        <div className="glass-card p-6">
          <h2 className="text-xl font-semibold text-erik-primary mb-4">New Product</h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Product Code</label>
              <input
                type="text"
                required
                value={formData.code}
                onChange={(e) => setFormData({...formData, code: e.target.value})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Product Name</label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-300 mb-2">Description</label>
              <input
                type="text"
                value={formData.description}
                onChange={(e) => setFormData({...formData, description: e.target.value})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Category</label>
              <input
                type="text"
                value={formData.category}
                onChange={(e) => setFormData({...formData, category: e.target.value})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Unit of Measure</label>
              <input
                type="text"
                value={formData.unit_of_measure}
                onChange={(e) => setFormData({...formData, unit_of_measure: e.target.value})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Unit Price (ZMW)</label>
              <input
                type="number"
                step="0.01"
                value={formData.unit_price}
                onChange={(e) => setFormData({...formData, unit_price: parseFloat(e.target.value)})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Cost Price (ZMW)</label>
              <input
                type="number"
                step="0.01"
                value={formData.cost_price}
                onChange={(e) => setFormData({...formData, cost_price: parseFloat(e.target.value)})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              />
            </div>
            <div className="md:col-span-2 flex gap-4">
              <button
                type="submit"
                className="bg-gradient-to-r from-erik-primary to-green-500 text-white px-6 py-2 rounded-lg font-semibold hover:shadow-lg hover:shadow-erik-primary/50 transition-all"
              >
                Create Product
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="bg-gray-700 text-white px-6 py-2 rounded-lg font-semibold hover:bg-gray-600 transition-all"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="glass-card overflow-hidden">
        <table className="w-full">
          <thead className="bg-erik-primary/10 border-b border-erik-primary/30">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase tracking-wider">Code</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase tracking-wider">Name</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase tracking-wider">Category</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase tracking-wider">Unit</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase tracking-wider">Unit Price</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {products.map((product) => (
              <tr key={product.id} className="hover:bg-erik-dark/50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">{product.code}</td>
                <td className="px-6 py-4 text-sm text-white">{product.name}</td>
                <td className="px-6 py-4 text-sm text-gray-400">{product.category || '-'}</td>
                <td className="px-6 py-4 text-sm text-gray-400">{product.unit_of_measure}</td>
                <td className="px-6 py-4 text-sm text-erik-primary font-medium">K {product.unit_price.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Products;
