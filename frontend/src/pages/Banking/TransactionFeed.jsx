import React, { useState, useEffect } from 'react';
import { Calendar, DollarSign, Filter, Download, CheckCircle, Clock } from 'lucide-react';
import api from '../../services/api';

const TransactionFeed = () => {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({
    status: 'all',
    direction: 'all',
    search: ''
  });

  useEffect(() => {
    fetchTransactions();
  }, []);

  const fetchTransactions = async () => {
    try {
      const response = await api.get('/api/banking/transactions', {
        params: filter.status !== 'all' ? { posting_status: filter.status } : {}
      });
      setTransactions(response.data);
    } catch (error) {
      console.error('Error fetching transactions:', error);
    } finally {
      setLoading(false);
    }
  };

  const filteredTransactions = transactions.filter(txn => {
    if (filter.direction !== 'all' && txn.direction !== filter.direction) return false;
    if (filter.search && !JSON.stringify(txn).toLowerCase().includes(filter.search.toLowerCase())) return false;
    return true;
  });

  const getDirectionBadge = (direction) => {
    return direction === 'inbound' ? (
      <span className="bg-green-500/20 text-green-400 px-2 py-1 rounded text-xs">Inbound</span>
    ) : (
      <span className="bg-red-500/20 text-red-400 px-2 py-1 rounded text-xs">Outbound</span>
    );
  };

  const getStatusBadge = (status) => {
    const badges = {
      pending: <span className="bg-yellow-500/20 text-yellow-400 px-2 py-1 rounded text-xs flex items-center gap-1"><Clock className="w-3 h-3" />Pending</span>,
      posted: <span className="bg-green-500/20 text-green-400 px-2 py-1 rounded text-xs flex items-center gap-1"><CheckCircle className="w-3 h-3" />Posted</span>
    };
    return badges[status] || <span className="bg-gray-500/20 text-gray-400 px-2 py-1 rounded text-xs">{status}</span>;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading transactions...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white">Transaction Feed</h1>
        <p className="text-gray-400 mt-1">View and manage imported bank transactions</p>
      </div>

      <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-4">
        <div className="flex flex-wrap gap-4">
          <input
            type="text"
            placeholder="Search transactions..."
            value={filter.search}
            onChange={(e) => setFilter({ ...filter, search: e.target.value })}
            className="flex-1 min-w-[200px] bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
          />
          
          <select
            value={filter.status}
            onChange={(e) => setFilter({ ...filter, status: e.target.value })}
            className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
          >
            <option value="all">All Status</option>
            <option value="pending">Pending</option>
            <option value="posted">Posted</option>
          </select>

          <select
            value={filter.direction}
            onChange={(e) => setFilter({ ...filter, direction: e.target.value })}
            className="bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
          >
            <option value="all">All Directions</option>
            <option value="inbound">Inbound</option>
            <option value="outbound">Outbound</option>
          </select>

          <button
            onClick={fetchTransactions}
            className="bg-teal-500 text-white px-4 py-2 rounded-lg hover:bg-teal-600 transition-colors flex items-center gap-2"
          >
            <Filter className="w-4 h-4" />
            Apply
          </button>
        </div>
      </div>

      <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-700/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Date</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Description</th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">Counterparty</th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-300 uppercase tracking-wider">Amount</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-300 uppercase tracking-wider">Direction</th>
                <th className="px-4 py-3 text-center text-xs font-medium text-gray-300 uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700">
              {filteredTransactions.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-4 py-8 text-center text-gray-400">
                    No transactions found
                  </td>
                </tr>
              ) : (
                filteredTransactions.map((txn) => (
                  <tr key={txn.id} className="hover:bg-gray-700/30 transition-colors">
                    <td className="px-4 py-3 text-sm text-white">
                      {new Date(txn.transaction_date).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3 text-sm text-white">
                      <div className="max-w-xs truncate">{txn.description || 'No description'}</div>
                      {txn.reference_number && (
                        <div className="text-xs text-gray-400">Ref: {txn.reference_number}</div>
                      )}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-300">
                      {txn.counterparty_name || '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-right font-mono">
                      <span className={txn.direction === 'inbound' ? 'text-green-400' : 'text-red-400'}>
                        {txn.direction === 'inbound' ? '+' : '-'}
                        {txn.currency} {txn.amount?.toLocaleString()}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-center">
                      {getDirectionBadge(txn.direction)}
                    </td>
                    <td className="px-4 py-3 text-center">
                      {getStatusBadge(txn.posting_status)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-white mb-4">Summary</h3>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gray-700/50 rounded-lg p-4">
            <div className="text-sm text-gray-400">Total Transactions</div>
            <div className="text-2xl font-bold text-white mt-1">{filteredTransactions.length}</div>
          </div>
          <div className="bg-green-500/10 rounded-lg p-4">
            <div className="text-sm text-green-400">Inbound</div>
            <div className="text-2xl font-bold text-green-400 mt-1">
              {filteredTransactions.filter(t => t.direction === 'inbound').length}
            </div>
          </div>
          <div className="bg-red-500/10 rounded-lg p-4">
            <div className="text-sm text-red-400">Outbound</div>
            <div className="text-2xl font-bold text-red-400 mt-1">
              {filteredTransactions.filter(t => t.direction === 'outbound').length}
            </div>
          </div>
          <div className="bg-yellow-500/10 rounded-lg p-4">
            <div className="text-sm text-yellow-400">Pending Post</div>
            <div className="text-2xl font-bold text-yellow-400 mt-1">
              {filteredTransactions.filter(t => t.posting_status === 'pending').length}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TransactionFeed;
