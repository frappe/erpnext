import React, { useState, useEffect } from 'react';
import { TruckIcon, Plus } from 'lucide-react';
import api from '../services/api';

function Suppliers() {
  const [suppliers, setSuppliers] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    supplier_code: '',
    name: '',
    email: '',
    phone: '',
    address: ''
  });

  useEffect(() => {
    fetchSuppliers();
  }, []);

  const fetchSuppliers = async () => {
    try {
      const response = await api.get('/api/suppliers');
      setSuppliers(response.data);
    } catch (error) {
      console.error('Error fetching suppliers:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.post('/api/suppliers', formData);
      setShowForm(false);
      setFormData({
        supplier_code: '',
        name: '',
        email: '',
        phone: '',
        address: ''
      });
      fetchSuppliers();
    } catch (error) {
      console.error('Error creating supplier:', error);
      alert('Failed to create supplier');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold gradient-text">Suppliers</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-gradient-to-r from-erik-primary to-green-500 text-white px-6 py-2 rounded-lg font-semibold hover:shadow-lg hover:shadow-erik-primary/50 transition-all flex items-center gap-2"
        >
          <Plus size={20} />
          Add Supplier
        </button>
      </div>

      {showForm && (
        <div className="glass-card p-6">
          <h2 className="text-xl font-semibold text-erik-primary mb-4">New Supplier</h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Supplier Code</label>
              <input
                type="text"
                required
                value={formData.supplier_code}
                onChange={(e) => setFormData({...formData, supplier_code: e.target.value})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Supplier Name</label>
              <input
                type="text"
                required
                value={formData.name}
                onChange={(e) => setFormData({...formData, name: e.target.value})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({...formData, email: e.target.value})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Phone</label>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({...formData, phone: e.target.value})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-300 mb-2">Address</label>
              <input
                type="text"
                value={formData.address}
                onChange={(e) => setFormData({...formData, address: e.target.value})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              />
            </div>
            <div className="md:col-span-2 flex gap-4">
              <button
                type="submit"
                className="bg-gradient-to-r from-erik-primary to-green-500 text-white px-6 py-2 rounded-lg font-semibold hover:shadow-lg hover:shadow-erik-primary/50 transition-all"
              >
                Create Supplier
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
              <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase tracking-wider">Email</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase tracking-wider">Phone</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {suppliers.map((supplier) => (
              <tr key={supplier.id} className="hover:bg-erik-dark/50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-erik-primary font-medium">{supplier.supplier_code}</td>
                <td className="px-6 py-4 text-sm text-white">{supplier.name}</td>
                <td className="px-6 py-4 text-sm text-gray-400">{supplier.email || '-'}</td>
                <td className="px-6 py-4 text-sm text-gray-400">{supplier.phone || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Suppliers;
