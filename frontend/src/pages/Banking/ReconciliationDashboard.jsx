import React, { useState, useEffect } from 'react';
import { CheckCircle, AlertCircle, XCircle, TrendingUp, RefreshCw } from 'lucide-react';
import api from '../../services/api';

const ReconciliationDashboard = () => {
  const [connections, setConnections] = useState([]);
  const [selectedConnection, setSelectedConnection] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchConnections();
  }, []);

  useEffect(() => {
    if (selectedConnection) {
      fetchReconciliationReport();
    }
  }, [selectedConnection]);

  const fetchConnections = async () => {
    try {
      const response = await api.get('/api/banking/connections');
      setConnections(response.data);
      if (response.data.length > 0) {
        setSelectedConnection(response.data[0].id);
      }
    } catch (error) {
      console.error('Error fetching connections:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchReconciliationReport = async () => {
    try {
      const endDate = new Date();
      const response = await api.get(`/api/banking/connections/${selectedConnection}/reconciliation-report`, {
        params: {
          as_of_date: endDate.toISOString()
        }
      });
      setReport(response.data);
    } catch (error) {
      console.error('Error fetching reconciliation report:', error);
    }
  };

  const runReconciliation = async () => {
    if (!confirm('Run auto-reconciliation for the last 30 days?')) return;

    try {
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - 30);

      const response = await api.post(`/api/banking/connections/${selectedConnection}/reconcile`, {
        from_date: startDate.toISOString(),
        to_date: endDate.toISOString(),
        auto_match: true
      });

      alert(`Reconciliation complete!\nAuto-matched: ${response.data.auto_matched}\nSuggested: ${response.data.suggested_matches}\nUnmatched: ${response.data.unmatched}`);
      fetchReconciliationReport();
    } catch (error) {
      alert('Error running reconciliation');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-400">Loading...</div>
      </div>
    );
  }

  if (connections.length === 0) {
    return (
      <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-12 text-center">
        <div className="text-6xl mb-4">📊</div>
        <h3 className="text-xl font-semibold text-white mb-2">No Bank Connections</h3>
        <p className="text-gray-400">Add a bank connection to start reconciliation</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white">Bank Reconciliation</h1>
          <p className="text-gray-400 mt-1">AI-powered transaction matching</p>
        </div>
        <button
          onClick={runReconciliation}
          className="flex items-center gap-2 bg-gradient-to-r from-teal-500 to-green-500 text-white px-4 py-2 rounded-lg hover:from-teal-600 hover:to-green-600 transition-all"
        >
          <RefreshCw className="w-5 h-5" />
          Run Reconciliation
        </button>
      </div>

      <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-4">
        <label className="block text-sm font-medium text-gray-300 mb-2">Select Bank Account</label>
        <select
          value={selectedConnection || ''}
          onChange={(e) => setSelectedConnection(parseInt(e.target.value))}
          className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2 text-white"
        >
          {connections.map((conn) => (
            <option key={conn.id} value={conn.id}>
              {conn.connection_name} - {conn.bank_name}
            </option>
          ))}
        </select>
      </div>

      {report && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className={`bg-gradient-to-br ${
              report.reconciliation_status === 'balanced' 
                ? 'from-green-500/20 to-teal-500/20 border-green-500/50' 
                : 'from-red-500/20 to-orange-500/20 border-red-500/50'
            } backdrop-blur-sm border rounded-xl p-6`}>
              <div className="flex items-center gap-3 mb-4">
                {report.reconciliation_status === 'balanced' ? (
                  <CheckCircle className="w-8 h-8 text-green-400" />
                ) : (
                  <AlertCircle className="w-8 h-8 text-red-400" />
                )}
                <div>
                  <div className="text-sm text-gray-400">Reconciliation Status</div>
                  <div className="text-2xl font-bold text-white capitalize">{report.reconciliation_status}</div>
                </div>
              </div>
              {report.difference !== 0 && (
                <div className="text-red-400 font-mono">
                  Difference: ZMW {Math.abs(report.difference).toLocaleString()}
                </div>
              )}
            </div>

            <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-6">
              <div className="flex items-center gap-3 mb-4">
                <TrendingUp className="w-8 h-8 text-teal-400" />
                <div>
                  <div className="text-sm text-gray-400">Balance Comparison</div>
                  <div className="text-2xl font-bold text-white">ZMW {report.bank_balance?.toLocaleString()}</div>
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">Bank Balance</span>
                  <span className="text-white font-mono">ZMW {report.bank_balance?.toLocaleString()}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-400">GL Balance</span>
                  <span className="text-white font-mono">ZMW {report.gl_balance?.toLocaleString()}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-4">
              <div className="text-sm text-gray-400">Unreconciled Bank Txns</div>
              <div className="text-2xl font-bold text-yellow-400 mt-1">{report.unreconciled_external_count}</div>
              <div className="text-xs text-gray-500 mt-1">
                ZMW {report.unreconciled_external_amount?.toLocaleString()}
              </div>
            </div>

            <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-4">
              <div className="text-sm text-gray-400">Unreconciled Journal Entries</div>
              <div className="text-2xl font-bold text-orange-400 mt-1">{report.unreconciled_journal_count}</div>
            </div>

            <div className="bg-green-500/10 backdrop-blur-sm border border-green-500/30 rounded-xl p-4">
              <div className="text-sm text-green-400">Matched Items</div>
              <div className="text-2xl font-bold text-green-400 mt-1">
                {(report.total_external || 0) - (report.unreconciled_external_count || 0)}
              </div>
            </div>

            <div className="bg-teal-500/10 backdrop-blur-sm border border-teal-500/30 rounded-xl p-4">
              <div className="text-sm text-teal-400">Match Rate</div>
              <div className="text-2xl font-bold text-teal-400 mt-1">
                {report.total_external > 0
                  ? Math.round(((report.total_external - report.unreconciled_external_count) / report.total_external) * 100)
                  : 0}%
              </div>
            </div>
          </div>

          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-xl p-6">
            <h3 className="text-lg font-semibold text-white mb-4">How It Works</h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="text-center">
                <div className="w-12 h-12 bg-teal-500/20 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-2xl">🔍</span>
                </div>
                <h4 className="font-semibold text-white mb-2">AI Matching</h4>
                <p className="text-sm text-gray-400">
                  Intelligent algorithms match bank transactions with journal entries based on amount, date, and description
                </p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-2xl">✓</span>
                </div>
                <h4 className="font-semibold text-white mb-2">Auto-Reconcile</h4>
                <p className="text-sm text-gray-400">
                  High-confidence matches (95%+) are automatically reconciled, saving you time
                </p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 bg-blue-500/20 rounded-full flex items-center justify-center mx-auto mb-3">
                  <span className="text-2xl">📊</span>
                </div>
                <h4 className="font-semibold text-white mb-2">Real-time Reports</h4>
                <p className="text-sm text-gray-400">
                  Get instant visibility into reconciliation status and outstanding items
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default ReconciliationDashboard;
