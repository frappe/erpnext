import { useState, useEffect } from 'react';
import { Upload, CheckCircle, XCircle, DollarSign, Building } from 'lucide-react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function BankReconciliation() {
  const [bankAccounts, setBankAccounts] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState('');
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    fetchBankAccounts();
  }, []);

  useEffect(() => {
    if (selectedAccount) {
      fetchTransactions();
    }
  }, [selectedAccount]);

  const fetchBankAccounts = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/banking/accounts`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setBankAccounts(response.data);
      if (response.data.length > 0) {
        setSelectedAccount(response.data[0].id);
      }
    } catch (error) {
      console.error('Error fetching bank accounts:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchTransactions = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/api/banking/transactions?bank_account_id=${selectedAccount}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTransactions(response.data);
    } catch (error) {
      console.error('Error fetching transactions:', error);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/api/banking/statements/import?bank_account_id=${selectedAccount}`, formData, {
        headers: { 
          Authorization: `Bearer ${token}`,
          'Content-Type': 'multipart/form-data'
        }
      });
      alert('Bank statement imported successfully!');
      fetchTransactions();
    } catch (error) {
      console.error('Error uploading statement:', error);
      alert('Failed to import statement');
    } finally {
      setUploading(false);
    }
  };

  const autoMatch = async () => {
    try {
      const token = localStorage.getItem('token');
      const today = new Date();
      const startDate = new Date(today.getFullYear(), today.getMonth() - 1, 1).toISOString().split('T')[0];
      const endDate = today.toISOString().split('T')[0];

      await axios.post(`${API_URL}/api/banking/reconciliation/auto-match`, {}, {
        params: {
          bank_account_id: selectedAccount,
          start_date: startDate,
          end_date: endDate
        },
        headers: { Authorization: `Bearer ${token}` }
      });
      alert('Auto-matching completed!');
      fetchTransactions();
    } catch (error) {
      console.error('Error auto-matching:', error);
      alert('Failed to auto-match transactions');
    }
  };

  const reconciledCount = transactions.filter(t => t.status === 'reconciled').length;
  const unreconciledCount = transactions.filter(t => t.status === 'unreconciled').length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-teal-900 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Bank Reconciliation</h1>
          <p className="text-gray-400">Import statements and match transactions</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-gradient-to-br from-blue-500/20 to-purple-500/20 backdrop-blur-sm rounded-lg p-6 border border-blue-500/30">
            <div className="flex items-center justify-between mb-2">
              <Building className="w-8 h-8 text-blue-400" />
              <span className="text-xs text-blue-300 font-medium">ACCOUNTS</span>
            </div>
            <p className="text-3xl font-bold text-white">{bankAccounts.length}</p>
            <p className="text-sm text-gray-400 mt-1">Bank accounts</p>
          </div>

          <div className="bg-gradient-to-br from-green-500/20 to-teal-500/20 backdrop-blur-sm rounded-lg p-6 border border-green-500/30">
            <div className="flex items-center justify-between mb-2">
              <CheckCircle className="w-8 h-8 text-green-400" />
              <span className="text-xs text-green-300 font-medium">RECONCILED</span>
            </div>
            <p className="text-3xl font-bold text-white">{reconciledCount}</p>
            <p className="text-sm text-gray-400 mt-1">Matched transactions</p>
          </div>

          <div className="bg-gradient-to-br from-orange-500/20 to-red-500/20 backdrop-blur-sm rounded-lg p-6 border border-orange-500/30">
            <div className="flex items-center justify-between mb-2">
              <XCircle className="w-8 h-8 text-orange-400" />
              <span className="text-xs text-orange-300 font-medium">UNRECONCILED</span>
            </div>
            <p className="text-3xl font-bold text-white">{unreconciledCount}</p>
            <p className="text-sm text-gray-400 mt-1">Pending matches</p>
          </div>
        </div>

        <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 mb-6 border border-gray-700">
          <div className="flex flex-col md:flex-row gap-4 items-center justify-between">
            <div className="flex-1 w-full">
              <label className="block text-sm font-medium text-gray-300 mb-2">Select Bank Account</label>
              <select
                value={selectedAccount}
                onChange={(e) => setSelectedAccount(e.target.value)}
                className="w-full px-4 py-2 bg-gray-900/50 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
              >
                {bankAccounts.map(account => (
                  <option key={account.id} value={account.id}>
                    {account.bank_name} - {account.account_number} ({account.currency})
                  </option>
                ))}
              </select>
            </div>
            <div className="flex gap-2">
              <label className="px-6 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all cursor-pointer flex items-center gap-2">
                <Upload className="w-5 h-5" />
                {uploading ? 'Uploading...' : 'Import CSV'}
                <input
                  type="file"
                  accept=".csv"
                  onChange={handleFileUpload}
                  className="hidden"
                  disabled={uploading}
                />
              </label>
              <button
                onClick={autoMatch}
                className="px-6 py-2 bg-gradient-to-r from-teal-500 to-green-500 text-white rounded-lg hover:from-teal-600 hover:to-green-600 transition-all"
              >
                Auto-Match
              </button>
            </div>
          </div>
        </div>

        <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
          <h2 className="text-xl font-bold text-white mb-4">Bank Transactions</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Date</th>
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Description</th>
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Type</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Amount</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Balance</th>
                  <th className="text-center py-3 px-4 text-gray-400 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {transactions.map((trans) => (
                  <tr key={trans.id} className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                    <td className="py-3 px-4 text-white">{trans.transaction_date}</td>
                    <td className="py-3 px-4 text-gray-300">{trans.description}</td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        trans.transaction_type === 'credit' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                      }`}>
                        {trans.transaction_type?.toUpperCase()}
                      </span>
                    </td>
                    <td className={`py-3 px-4 text-right font-semibold ${
                      trans.transaction_type === 'credit' ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {trans.transaction_type === 'credit' ? '+' : '-'}
                      ZMW {trans.amount?.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-right text-white">
                      ZMW {trans.balance?.toLocaleString()}
                    </td>
                    <td className="py-3 px-4 text-center">
                      {trans.status === 'reconciled' ? (
                        <CheckCircle className="w-5 h-5 text-green-400 mx-auto" />
                      ) : (
                        <XCircle className="w-5 h-5 text-orange-400 mx-auto" />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {transactions.length === 0 && (
            <div className="text-center py-12">
              <DollarSign className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400 text-lg">No transactions yet</p>
              <p className="text-gray-500 text-sm mt-2">Import a bank statement to get started</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
