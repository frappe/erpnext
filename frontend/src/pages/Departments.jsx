import { useState, useEffect } from 'react';
import { Building2, Plus, Edit2, Check, X } from 'lucide-react';
import axios from 'axios';

export default function Departments() {
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [formData, setFormData] = useState({
    dept_code: '',
    dept_name: '',
    parent_dept_id: '',
    manager_id: '',
    cost_center_code: ''
  });
  const [error, setError] = useState('');

  useEffect(() => {
    fetchDepartments();
  }, []);

  const fetchDepartments = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('/api/departments', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDepartments(response.data);
    } catch (error) {
      console.error('Error fetching departments:', error);
      setError('Failed to load departments');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const token = localStorage.getItem('token');
      const config = {
        headers: { Authorization: `Bearer ${token}` }
      };

      if (editingId) {
        await axios.put(`/api/departments/${editingId}`, formData, config);
      } else {
        await axios.post('/api/departments', formData, config);
      }

      setShowForm(false);
      setEditingId(null);
      setFormData({
        dept_code: '',
        dept_name: '',
        parent_dept_id: '',
        manager_id: '',
        cost_center_code: ''
      });
      fetchDepartments();
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to save department');
    }
  };

  const handleEdit = (dept) => {
    setFormData({
      dept_code: dept.dept_code,
      dept_name: dept.dept_name,
      parent_dept_id: dept.parent_dept_id || '',
      manager_id: dept.manager_id || '',
      cost_center_code: dept.cost_center_code || ''
    });
    setEditingId(dept.id);
    setShowForm(true);
  };

  const handleCancel = () => {
    setShowForm(false);
    setEditingId(null);
    setFormData({
      dept_code: '',
      dept_name: '',
      parent_dept_id: '',
      manager_id: '',
      cost_center_code: ''
    });
    setError('');
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-white">Loading...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-teal-900 p-8">
      <div className="max-w-6xl mx-auto">
        <div className="flex justify-between items-center mb-8">
          <div className="flex items-center gap-3">
            <Building2 className="text-teal-400" size={32} />
            <h1 className="text-3xl font-bold text-white">Department Management</h1>
          </div>
          {!showForm && (
            <button
              onClick={() => setShowForm(true)}
              className="flex items-center gap-2 bg-teal-500 hover:bg-teal-600 text-white px-6 py-3 rounded-lg transition-colors"
            >
              <Plus size={20} />
              Add Department
            </button>
          )}
        </div>

        {error && (
          <div className="bg-red-500/20 border border-red-500 text-red-200 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {showForm && (
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-lg p-6 mb-8">
            <h2 className="text-xl font-semibold text-white mb-4">
              {editingId ? 'Edit Department' : 'New Department'}
            </h2>
            <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-gray-300 mb-2">Department Code *</label>
                <input
                  type="text"
                  value={formData.dept_code}
                  onChange={(e) => setFormData({ ...formData, dept_code: e.target.value })}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600 focus:outline-none focus:border-teal-400"
                  required
                />
              </div>
              <div>
                <label className="block text-gray-300 mb-2">Department Name *</label>
                <input
                  type="text"
                  value={formData.dept_name}
                  onChange={(e) => setFormData({ ...formData, dept_name: e.target.value })}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600 focus:outline-none focus:border-teal-400"
                  required
                />
              </div>
              <div>
                <label className="block text-gray-300 mb-2">Parent Department</label>
                <select
                  value={formData.parent_dept_id}
                  onChange={(e) => setFormData({ ...formData, parent_dept_id: e.target.value })}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600 focus:outline-none focus:border-teal-400"
                >
                  <option value="">None (Top Level)</option>
                  {departments.filter(d => d.id !== editingId).map(dept => (
                    <option key={dept.id} value={dept.id}>
                      {dept.dept_name} ({dept.dept_code})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-gray-300 mb-2">Cost Center Code</label>
                <input
                  type="text"
                  value={formData.cost_center_code}
                  onChange={(e) => setFormData({ ...formData, cost_center_code: e.target.value })}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600 focus:outline-none focus:border-teal-400"
                />
              </div>
              <div className="col-span-2 flex gap-3 mt-4">
                <button
                  type="submit"
                  className="flex items-center gap-2 bg-teal-500 hover:bg-teal-600 text-white px-6 py-2 rounded-lg transition-colors"
                >
                  <Check size={20} />
                  {editingId ? 'Update' : 'Create'}
                </button>
                <button
                  type="button"
                  onClick={handleCancel}
                  className="flex items-center gap-2 bg-gray-600 hover:bg-gray-700 text-white px-6 py-2 rounded-lg transition-colors"
                >
                  <X size={20} />
                  Cancel
                </button>
              </div>
            </form>
          </div>
        )}

        <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-lg overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-900/50">
              <tr>
                <th className="text-left text-gray-300 px-6 py-4">Code</th>
                <th className="text-left text-gray-300 px-6 py-4">Department Name</th>
                <th className="text-left text-gray-300 px-6 py-4">Cost Center</th>
                <th className="text-left text-gray-300 px-6 py-4">Status</th>
                <th className="text-left text-gray-300 px-6 py-4">Actions</th>
              </tr>
            </thead>
            <tbody>
              {departments.length === 0 ? (
                <tr>
                  <td colSpan="5" className="text-center text-gray-400 px-6 py-8">
                    No departments found. Create your first department to get started.
                  </td>
                </tr>
              ) : (
                departments.map((dept) => (
                  <tr key={dept.id} className="border-t border-gray-700 hover:bg-gray-700/30">
                    <td className="text-white px-6 py-4">{dept.dept_code}</td>
                    <td className="text-white px-6 py-4">{dept.dept_name}</td>
                    <td className="text-gray-300 px-6 py-4">
                      {dept.cost_center_code || '-'}
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-3 py-1 rounded-full text-sm ${
                        dept.is_active 
                          ? 'bg-green-500/20 text-green-300' 
                          : 'bg-red-500/20 text-red-300'
                      }`}>
                        {dept.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <button
                        onClick={() => handleEdit(dept)}
                        className="flex items-center gap-2 text-teal-400 hover:text-teal-300 transition-colors"
                      >
                        <Edit2 size={18} />
                        Edit
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
