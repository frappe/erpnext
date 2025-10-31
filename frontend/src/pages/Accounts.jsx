import React, { useState, useEffect } from 'react';
import { Plus, BookOpen } from 'lucide-react';
import { accounts } from '../services/api';

function Accounts() {
  const [accountList, setAccountList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    code: '',
    name: '',
    account_type: 'asset',
  });

  const loadAccounts = () => {
    accounts.getAll()
      .then(response => {
        setAccountList(response.data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadAccounts();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await accounts.create(formData);
      setShowForm(false);
      setFormData({ code: '', name: '', account_type: 'asset' });
      loadAccounts();
    } catch (error) {
      alert('Failed to create account');
    }
  };

  const accountTypes = [
    { value: 'asset', label: 'Asset', color: 'text-blue-400' },
    { value: 'liability', label: 'Liability', color: 'text-red-400' },
    { value: 'equity', label: 'Equity', color: 'text-yellow-400' },
    { value: 'revenue', label: 'Revenue', color: 'text-green-400' },
    { value: 'expense', label: 'Expense', color: 'text-purple-400' },
  ];

  if (loading) {
    return <div className="text-erik-primary">Loading...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Chart of Accounts</h1>
          <p className="text-gray-400">Manage your accounting structure</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn-primary flex items-center"
        >
          <Plus size={20} className="mr-2" />
          Add Account
        </button>
      </div>

      {showForm && (
        <div className="card mb-6">
          <h3 className="text-xl font-semibold text-white mb-4">New Account</h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Account Code
              </label>
              <input
                type="text"
                required
                className="input-field"
                placeholder="6000"
                value={formData.code}
                onChange={(e) => setFormData({ ...formData, code: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Account Name
              </label>
              <input
                type="text"
                required
                className="input-field"
                placeholder="Marketing Expenses"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
            <div className="col-span-2">
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Account Type
              </label>
              <select
                className="input-field"
                value={formData.account_type}
                onChange={(e) => setFormData({ ...formData, account_type: e.target.value })}
              >
                {accountTypes.map(type => (
                  <option key={type.value} value={type.value}>{type.label}</option>
                ))}
              </select>
            </div>
            <div className="col-span-2 flex space-x-4">
              <button type="submit" className="btn-primary">
                Create Account
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="card">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-erik-primary/20">
                <th className="text-left py-3 px-4 text-gray-400 font-medium">Code</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">Account Name</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">Type</th>
                <th className="text-left py-3 px-4 text-gray-400 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {accountList.length === 0 ? (
                <tr>
                  <td colSpan="4" className="text-center py-8 text-gray-400">
                    No accounts yet
                  </td>
                </tr>
              ) : (
                accountList.map((account) => {
                  const typeInfo = accountTypes.find(t => t.value === account.account_type);
                  return (
                    <tr key={account.id} className="border-b border-erik-primary/10 hover:bg-erik-dark/30">
                      <td className="py-3 px-4 text-white font-mono">{account.code}</td>
                      <td className="py-3 px-4 text-white">{account.name}</td>
                      <td className="py-3 px-4">
                        <span className={typeInfo?.color || 'text-gray-400'}>
                          {typeInfo?.label || account.account_type}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className={`text-xs px-2 py-1 rounded ${
                          account.is_active
                            ? 'bg-green-500/20 text-green-400'
                            : 'bg-gray-500/20 text-gray-400'
                        }`}>
                          {account.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default Accounts;
