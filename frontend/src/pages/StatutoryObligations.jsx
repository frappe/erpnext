import React, { useState, useEffect } from 'react';
import { Calendar, AlertTriangle, CheckCircle2, Clock, DollarSign, Plus, X, FileText } from 'lucide-react';
import api from '../services/api';

export default function StatutoryObligations() {
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showAddModal, setShowAddModal] = useState(false);
  const [newObligation, setNewObligation] = useState({
    obligation_type: '',
    description: '',
    frequency: 'monthly',
    due_day: 10,
    due_date: '',
    amount: ''
  });

  const obligationTypes = [
    { value: 'PAYE', label: 'PAYE (Pay As You Earn)', authority: 'ZRA', due_day: 10 },
    { value: 'NAPSA', label: 'NAPSA Contributions', authority: 'NAPSA', due_day: 10 },
    { value: 'NHIMA', label: 'NHIMA Contributions', authority: 'NHIMA', due_day: 10 },
    { value: 'SDL', label: 'Skills Development Levy', authority: 'ZRA', due_day: 14 },
    { value: 'VAT', label: 'VAT / Smart Invoice', authority: 'ZRA', due_day: 18 },
    { value: 'WVAT', label: 'Withholding VAT', authority: 'ZRA', due_day: 14 },
    { value: 'WCF', label: 'Workers\' Compensation Fund', authority: 'WCF', due_day: 10 },
    { value: 'PTT', label: 'Property Transfer Tax', authority: 'ZRA', due_day: 30 },
    { value: 'STAMP_DUTY', label: 'Stamp Duty', authority: 'ZRA', due_day: 30 },
    { value: 'TOURISM_LEVY', label: 'Tourism Levy', authority: 'ZRA', due_day: 15 }
  ];

  useEffect(() => {
    fetchDashboard();
  }, []);

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const response = await api.get('/api/statutory-obligations/dashboard');
      setDashboard(response.data);
    } catch (error) {
      console.error('Error fetching statutory dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleMarkAsPaid = async (obligationId) => {
    try {
      const today = new Date().toISOString().split('T')[0];
      await api.put(`/api/statutory-obligations/${obligationId}`, {
        status: 'paid',
        paid_date: today
      });
      fetchDashboard();
    } catch (error) {
      console.error('Error marking obligation as paid:', error);
    }
  };

  const handleAddObligation = async (e) => {
    e.preventDefault();
    try {
      await api.post('/api/statutory-obligations', newObligation);
      setShowAddModal(false);
      setNewObligation({
        obligation_type: '',
        description: '',
        frequency: 'monthly',
        due_day: 10,
        due_date: '',
        amount: ''
      });
      fetchDashboard();
    } catch (error) {
      console.error('Error adding obligation:', error);
    }
  };

  const formatCurrency = (amount) => {
    return `ZMW ${amount ? parseFloat(amount).toLocaleString('en-ZM', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : '0.00'}`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  };

  const getDaysUntilDue = (dueDate) => {
    const today = new Date();
    const due = new Date(dueDate);
    const diffTime = due - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-emerald-500 mx-auto mb-4"></div>
          <p className="text-gray-400">Loading statutory obligations...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white">Statutory Obligations</h1>
          <p className="text-gray-400 mt-1">Monitor and track all statutory compliance deadlines</p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white rounded-lg transition-colors"
        >
          <Plus className="w-5 h-5" />
          <span>Add Obligation</span>
        </button>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="card border-l-4 border-blue-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Total Obligations</p>
              <p className="text-3xl font-bold text-white mt-2">{dashboard?.total_obligations || 0}</p>
            </div>
            <FileText className="w-8 h-8 text-blue-500" />
          </div>
        </div>

        <div className="card border-l-4 border-yellow-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Upcoming (30 days)</p>
              <p className="text-3xl font-bold text-white mt-2">{dashboard?.upcoming_count || 0}</p>
              <p className="text-sm text-yellow-400 mt-1">{formatCurrency(dashboard?.total_due_amount || 0)}</p>
            </div>
            <Clock className="w-8 h-8 text-yellow-500" />
          </div>
        </div>

        <div className="card border-l-4 border-red-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Overdue</p>
              <p className="text-3xl font-bold text-white mt-2">{dashboard?.overdue_count || 0}</p>
              <p className="text-sm text-red-400 mt-1">{formatCurrency(dashboard?.total_overdue_amount || 0)}</p>
            </div>
            <AlertTriangle className="w-8 h-8 text-red-500" />
          </div>
        </div>

        <div className="card border-l-4 border-emerald-500">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Total Due</p>
              <p className="text-2xl font-bold text-white mt-2">{formatCurrency((dashboard?.total_due_amount || 0) + (dashboard?.total_overdue_amount || 0))}</p>
            </div>
            <DollarSign className="w-8 h-8 text-emerald-500" />
          </div>
        </div>
      </div>

      {/* Overdue Obligations Alert */}
      {dashboard?.overdue_count > 0 && (
        <div className="card bg-red-500/10 border-2 border-red-500/30">
          <div className="flex items-start space-x-3">
            <AlertTriangle className="w-6 h-6 text-red-400 flex-shrink-0 mt-1" />
            <div>
              <h3 className="text-lg font-semibold text-red-400 mb-2">⚠️ Overdue Obligations Require Immediate Attention</h3>
              <p className="text-gray-300 text-sm">
                You have {dashboard.overdue_count} overdue statutory obligation(s) totaling {formatCurrency(dashboard.total_overdue_amount)}. 
                Late payments may incur penalties and interest charges.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Overdue Obligations */}
      {dashboard?.overdue_obligations?.length > 0 && (
        <div className="card">
          <h3 className="text-xl font-bold text-red-400 mb-4 flex items-center">
            <AlertTriangle className="w-5 h-5 mr-2" />
            Overdue Obligations
          </h3>
          <div className="space-y-3">
            {dashboard.overdue_obligations.map((obligation) => (
              <div key={obligation.id} className="p-4 rounded-lg bg-red-500/10 border border-red-500/30">
                <div className="flex items-center justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3">
                      <h4 className="text-lg font-semibold text-white">{obligation.obligation_type}</h4>
                      <span className="px-3 py-1 rounded-full text-xs font-medium bg-red-500 text-white">
                        {Math.abs(getDaysUntilDue(obligation.due_date))} days overdue
                      </span>
                    </div>
                    <p className="text-sm text-gray-400 mt-1">{obligation.description}</p>
                    <div className="flex items-center space-x-6 mt-2 text-sm">
                      <span className="text-gray-400">Due: <strong className="text-red-400">{formatDate(obligation.due_date)}</strong></span>
                      <span className="text-gray-400">Amount: <strong className="text-white">{formatCurrency(obligation.amount)}</strong></span>
                      <span className="text-gray-400">Frequency: <strong className="text-white">{obligation.frequency}</strong></span>
                    </div>
                  </div>
                  <button
                    onClick={() => handleMarkAsPaid(obligation.id)}
                    className="ml-4 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg text-sm transition-colors"
                  >
                    Mark as Paid
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upcoming Obligations */}
      {dashboard?.upcoming_obligations?.length > 0 && (
        <div className="card">
          <h3 className="text-xl font-bold text-white mb-4 flex items-center">
            <Calendar className="w-5 h-5 mr-2" />
            Upcoming Obligations (Next 30 Days)
          </h3>
          <div className="space-y-3">
            {dashboard.upcoming_obligations.map((obligation) => {
              const daysUntil = getDaysUntilDue(obligation.due_date);
              const isUrgent = daysUntil <= 7;
              
              return (
                <div 
                  key={obligation.id} 
                  className={`p-4 rounded-lg ${isUrgent ? 'bg-yellow-500/10 border border-yellow-500/30' : 'bg-white/5 border border-white/10'}`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3">
                        <h4 className="text-lg font-semibold text-white">{obligation.obligation_type}</h4>
                        <span className={`px-3 py-1 rounded-full text-xs font-medium ${isUrgent ? 'bg-yellow-500 text-black' : 'bg-blue-500 text-white'}`}>
                          {daysUntil} days remaining
                        </span>
                      </div>
                      <p className="text-sm text-gray-400 mt-1">{obligation.description}</p>
                      <div className="flex items-center space-x-6 mt-2 text-sm">
                        <span className="text-gray-400">Due: <strong className="text-white">{formatDate(obligation.due_date)}</strong></span>
                        <span className="text-gray-400">Amount: <strong className="text-white">{formatCurrency(obligation.amount)}</strong></span>
                        <span className="text-gray-400">Frequency: <strong className="text-white">{obligation.frequency}</strong></span>
                      </div>
                    </div>
                    <button
                      onClick={() => handleMarkAsPaid(obligation.id)}
                      className="ml-4 px-4 py-2 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg text-sm transition-colors"
                    >
                      Mark as Paid
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Empty State */}
      {dashboard?.total_obligations === 0 && (
        <div className="card text-center py-12">
          <Calendar className="w-16 h-16 text-gray-600 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">No Statutory Obligations Yet</h3>
          <p className="text-gray-400 mb-6">Add your statutory obligations to start tracking compliance deadlines</p>
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white rounded-lg transition-colors"
          >
            <Plus className="w-5 h-5" />
            <span>Add First Obligation</span>
          </button>
        </div>
      )}

      {/* Add Obligation Modal */}
      {showAddModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-gradient-to-br from-slate-800 to-slate-900 rounded-xl shadow-2xl max-w-2xl w-full border border-white/10">
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-bold text-white">Add Statutory Obligation</h2>
                <button
                  onClick={() => setShowAddModal(false)}
                  className="p-2 rounded-lg hover:bg-white/10 transition-colors"
                >
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              </div>

              <form onSubmit={handleAddObligation} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Obligation Type</label>
                  <select
                    value={newObligation.obligation_type}
                    onChange={(e) => {
                      const selected = obligationTypes.find(t => t.value === e.target.value);
                      setNewObligation({
                        ...newObligation,
                        obligation_type: e.target.value,
                        description: selected?.label || '',
                        due_day: selected?.due_day || 10
                      });
                    }}
                    className="input-field"
                    required
                  >
                    <option value="">Select obligation type</option>
                    {obligationTypes.map(type => (
                      <option key={type.value} value={type.value}>{type.label}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Description</label>
                  <input
                    type="text"
                    value={newObligation.description}
                    onChange={(e) => setNewObligation({ ...newObligation, description: e.target.value })}
                    className="input-field"
                    placeholder="Brief description"
                    required
                  />
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Frequency</label>
                    <select
                      value={newObligation.frequency}
                      onChange={(e) => setNewObligation({ ...newObligation, frequency: e.target.value })}
                      className="input-field"
                      required
                    >
                      <option value="monthly">Monthly</option>
                      <option value="quarterly">Quarterly</option>
                      <option value="annually">Annually</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Due Date</label>
                    <input
                      type="date"
                      value={newObligation.due_date}
                      onChange={(e) => setNewObligation({ ...newObligation, due_date: e.target.value })}
                      className="input-field"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">Amount (ZMW)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={newObligation.amount}
                    onChange={(e) => setNewObligation({ ...newObligation, amount: e.target.value })}
                    className="input-field"
                    placeholder="0.00"
                  />
                </div>

                <div className="flex items-center justify-end space-x-3 mt-6">
                  <button
                    type="button"
                    onClick={() => setShowAddModal(false)}
                    className="px-6 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-white transition-colors"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    className="px-6 py-2 rounded-lg bg-gradient-to-r from-emerald-500 to-teal-500 hover:from-emerald-600 hover:to-teal-600 text-white font-semibold transition-colors"
                  >
                    Add Obligation
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
