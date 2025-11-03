import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Plus, RefreshCw, Trash2, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import api from '../../services/api';

const BankConnections = () => {
  const [connections, setConnections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);

  useEffect(() => {
    fetchConnections();
  }, []);

  const fetchConnections = async () => {
    try {
      const response = await api.get('/api/banking/connections');
      setConnections(response.data);
    } catch (error) {
      console.error('Error fetching connections:', error);
    } finally {
      setLoading(false);
    }
  };

  const testConnection = async (id) => {
    try {
      const response = await api.post(`/api/banking/connections/${id}/test`);
      if (response.data.is_connected) {
        alert('Connection successful!');
      } else {
        alert(`Connection failed: ${response.data.status_message}`);
      }
      fetchConnections();
    } catch (error) {
      alert('Error testing connection');
    }
  };

  const syncTransactions = async (id) => {
    if (!confirm('Sync transactions for the last 30 days?')) return;
    
    try {
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - 30);
      
      const response = await api.post(`/api/banking/connections/${id}/sync`, {
        from_date: startDate.toISOString(),
        to_date: endDate.toISOString()
      });
      
      alert(`Synced ${response.data.transactions_synced} transactions`);
      fetchConnections();
    } catch (error) {
      alert('Error syncing transactions');
    }
  };

  const deleteConnection = async (id) => {
    if (!confirm('Delete this bank connection?')) return;
    
    try {
      await api.delete(`/api/banking/connections/${id}`);
      fetchConnections();
    } catch (error) {
      alert('Error deleting connection');
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'connected':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-400" />;
      default:
        return <AlertCircle className="w-5 h-5 text-yellow-400" />;
    }
  };

  const getBankLogo = (providerCode) => {
    const logos = {
      zanaco: '🏦',
      absa: '🏦',
      stanbic: '🏦',
      fnb: '🏦',
      atlas_mara: '🏦'
    };
    return logos[providerCode] || '🏦';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading connections...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white">Bank Connections</h1>
          <p className="text-gray-400 mt-1">Manage your banking integrations</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center gap-2 bg-gradient-to-r from-teal-500 to-green-500 text-white px-4 py-2 rounded-lg hover:from-teal-600 hover:to-green-600 transition-all"
        >
          <Plus className="w-5 h-5" />
          Add Connection
        </button>
      </div>

      {connections.length === 0 ? (
        <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-12 text-center">
          <div className="text-6xl mb-4">🏦</div>
          <h3 className="text-xl font-semibold text-white mb-2">No Bank Connections</h3>
          <p className="text-gray-400 mb-6">Connect your bank accounts to automate transactions</p>
          <button
            onClick={() => setShowAddModal(true)}
            className="bg-teal-500 text-white px-6 py-2 rounded-lg hover:bg-teal-600 transition-colors"
          >
            Add Your First Connection
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {connections.map((conn) => (
            <div
              key={conn.id}
              className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-6 hover:border-teal-500 transition-all"
            >
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="text-4xl">{getBankLogo(conn.provider_code)}</div>
                  <div>
                    <h3 className="text-lg font-semibold text-white">{conn.connection_name}</h3>
                    <p className="text-sm text-gray-400">{conn.bank_name}</p>
                  </div>
                </div>
                {getStatusIcon(conn.status)}
              </div>

              <div className="space-y-2 mb-4">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Account</span>
                  <span className="text-white">****{conn.account_number?.slice(-4)}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Type</span>
                  <span className="text-white capitalize">{conn.connection_type}</span>
                </div>
                {conn.last_sync_at && (
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Last Sync</span>
                    <span className="text-white">{new Date(conn.last_sync_at).toLocaleDateString()}</span>
                  </div>
                )}
              </div>

              <div className="flex gap-2 pt-4 border-t border-gray-700">
                <button
                  onClick={() => testConnection(conn.id)}
                  className="flex-1 flex items-center justify-center gap-1 bg-gray-700 text-white px-3 py-2 rounded-lg hover:bg-gray-600 transition-colors text-sm"
                >
                  <CheckCircle className="w-4 h-4" />
                  Test
                </button>
                <button
                  onClick={() => syncTransactions(conn.id)}
                  className="flex-1 flex items-center justify-center gap-1 bg-teal-500 text-white px-3 py-2 rounded-lg hover:bg-teal-600 transition-colors text-sm"
                >
                  <RefreshCw className="w-4 h-4" />
                  Sync
                </button>
                <button
                  onClick={() => deleteConnection(conn.id)}
                  className="flex items-center justify-center bg-red-500 text-white px-3 py-2 rounded-lg hover:bg-red-600 transition-colors text-sm"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showAddModal && (
        <AddConnectionModal onClose={() => setShowAddModal(false)} onSuccess={fetchConnections} />
      )}
    </div>
  );
};

const AddConnectionModal = ({ onClose, onSuccess }) => {
  const [formData, setFormData] = useState({
    connection_name: '',
    provider_code: 'zanaco',
    bank_name: '',
    account_number: '',
    connection_type: 'api',
    api_username: '',
    api_key: '',
    api_secret: '',
    api_endpoint: ''
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.post('/api/banking/connections', formData);
      alert('Bank connection added successfully!');
      onSuccess();
      onClose();
    } catch (error) {
      alert('Error adding connection: ' + (error.response?.data?.detail || 'Unknown error'));
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-gray-800 rounded-xl p-6 max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <h2 className="text-2xl font-bold text-white mb-6">Add Bank Connection</h2>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">Connection Name</label>
            <input
              type="text"
              value={formData.connection_name}
              onChange={(e) => setFormData({ ...formData, connection_name: e.target.value })}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Bank Provider</label>
              <select
                value={formData.provider_code}
                onChange={(e) => setFormData({ ...formData, provider_code: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
              >
                <option value="zanaco">ZANACO</option>
                <option value="absa">ABSA Bank Zambia</option>
                <option value="stanbic">Stanbic Bank</option>
                <option value="fnb">FNB Zambia</option>
                <option value="atlas_mara">Atlas Mara</option>
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Account Number</label>
              <input
                type="text"
                value={formData.account_number}
                onChange={(e) => setFormData({ ...formData, account_number: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">API Username</label>
            <input
              type="text"
              value={formData.api_username}
              onChange={(e) => setFormData({ ...formData, api_username: e.target.value })}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">API Key</label>
              <input
                type="password"
                value={formData.api_key}
                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">API Secret</label>
              <input
                type="password"
                value={formData.api_secret}
                onChange={(e) => setFormData({ ...formData, api_secret: e.target.value })}
                className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">API Endpoint</label>
            <input
              type="url"
              value={formData.api_endpoint}
              onChange={(e) => setFormData({ ...formData, api_endpoint: e.target.value })}
              className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
              placeholder="https://api.example.com"
            />
          </div>

          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 bg-gray-700 text-white px-4 py-2 rounded-lg hover:bg-gray-600 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 bg-teal-500 text-white px-4 py-2 rounded-lg hover:bg-teal-600 transition-colors"
            >
              Add Connection
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default BankConnections;
