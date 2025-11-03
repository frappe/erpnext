import React, { useState, useEffect } from 'react';
import { Calendar, AlertTriangle, CheckCircle, Clock, TrendingUp } from 'lucide-react';
import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000';

export default function Compliance() {
  const [obligations, setObligations] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const [selectedMonth, setSelectedMonth] = useState(new Date().getMonth() + 1);
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());

  useEffect(() => {
    loadData();
  }, [filter]);

  const loadData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const [dashRes, obligRes] = await Promise.all([
        axios.get(`${API_URL}/api/compliance/dashboard`, { headers }),
        axios.get(`${API_URL}/api/compliance/obligations`, {
          headers,
          params: filter !== 'all' ? { status: filter } : {}
        })
      ]);

      setDashboard(dashRes.data);
      setObligations(obligRes.data.obligations || []);
      setLoading(false);
    } catch (error) {
      console.error('Error loading compliance data:', error);
      setLoading(false);
    }
  };

  const generateObligations = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_URL}/api/compliance/obligations/generate-monthly/${selectedYear}/${selectedMonth}`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      alert(`Generated ${response.data.count} obligations for ${selectedYear}-${String(selectedMonth).padStart(2, '0')}`);
      loadData();
    } catch (error) {
      alert('Error generating obligations: ' + (error.response?.data?.detail || error.message));
    }
  };

  const checkAlerts = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_URL}/api/compliance/check-alerts`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      alert(`Sent ${response.data.alerts_sent} alert notifications`);
      loadData();
    } catch (error) {
      alert('Error checking alerts: ' + (error.response?.data?.detail || error.message));
    }
  };

  const updateObligation = async (id, updates) => {
    try {
      const token = localStorage.getItem('token');
      await axios.put(
        `${API_URL}/api/compliance/obligations/${id}`,
        updates,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      loadData();
    } catch (error) {
      alert('Error updating obligation: ' + (error.response?.data?.detail || error.message));
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      pending: 'bg-yellow-100 text-yellow-800',
      submitted: 'bg-blue-100 text-blue-800',
      paid: 'bg-green-100 text-green-800',
      overdue: 'bg-red-100 text-red-800'
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  const getComplianceColor = (percentage) => {
    if (percentage >= 90) return 'text-green-600';
    if (percentage >= 70) return 'text-yellow-600';
    return 'text-red-600';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-xl">Loading compliance data...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Statutory Compliance</h1>
            <p className="text-gray-600 mt-1">Track ZRA, NAPSA, NHIMA & statutory obligations</p>
          </div>
          
          <div className="flex gap-3">
            <button
              onClick={checkAlerts}
              className="px-4 py-2 bg-orange-600 text-white rounded-lg hover:bg-orange-700 flex items-center gap-2"
            >
              <Bell className="w-4 h-4" />
              Check Alerts
            </button>
            <button
              onClick={generateObligations}
              className="px-4 py-2 bg-[#00D9A3] text-white rounded-lg hover:bg-[#00c092] flex items-center gap-2"
            >
              <Calendar className="w-4 h-4" />
              Generate Obligations
            </button>
          </div>
        </div>

        {/* Generate Obligations Panel */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
          <div className="flex items-center gap-4">
            <label className="text-sm font-medium text-gray-700">Generate for:</label>
            <select
              value={selectedMonth}
              onChange={(e) => setSelectedMonth(parseInt(e.target.value))}
              className="px-3 py-2 border rounded-lg"
            >
              {[...Array(12)].map((_, i) => (
                <option key={i} value={i + 1}>
                  {new Date(2000, i).toLocaleString('default', { month: 'long' })}
                </option>
              ))}
            </select>
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(parseInt(e.target.value))}
              className="px-3 py-2 border rounded-lg"
            >
              {[2024, 2025, 2026].map((year) => (
                <option key={year} value={year}>{year}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Compliance Dashboard Stats */}
        {dashboard && (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Overall Compliance</p>
                  <p className={`text-3xl font-bold ${getComplianceColor(dashboard.overall_compliance_percentage)}`}>
                    {dashboard.overall_compliance_percentage.toFixed(1)}%
                  </p>
                </div>
                <TrendingUp className={`w-10 h-10 ${getComplianceColor(dashboard.overall_compliance_percentage)}`} />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Total Obligations</p>
                  <p className="text-3xl font-bold text-gray-900">{dashboard.total_obligations}</p>
                </div>
                <Calendar className="w-10 h-10 text-blue-600" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Completed</p>
                  <p className="text-3xl font-bold text-green-600">{dashboard.by_status.paid || 0}</p>
                </div>
                <CheckCircle className="w-10 h-10 text-green-600" />
              </div>
            </div>

            <div className="bg-white rounded-lg shadow-sm p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-gray-600">Overdue</p>
                  <p className="text-3xl font-bold text-red-600">{dashboard.by_status.overdue || 0}</p>
                </div>
                <AlertTriangle className="w-10 h-10 text-red-600" />
              </div>
            </div>
          </div>
        )}


        {/* Filters */}
        <div className="flex gap-2 mb-6">
          {['all', 'pending', 'submitted', 'paid', 'overdue'].map((status) => (
            <button
              key={status}
              onClick={() => setFilter(status)}
              className={`px-4 py-2 rounded-lg ${
                filter === status
                  ? 'bg-[#00D9A3] text-white'
                  : 'bg-white text-gray-700 hover:bg-gray-100'
              }`}
            >
              {status.charAt(0).toUpperCase() + status.slice(1)}
            </button>
          ))}
        </div>

        {/* Obligations Table */}
        <div className="bg-white rounded-lg shadow-sm overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Period</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Due Date</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Amount</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Compliance %</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Actions</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {obligations.map((obl) => (
                <tr key={obl.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="font-medium text-gray-900">{obl.obligation_type}</div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {obl.year}-{String(obl.month).padStart(2, '0')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                    {new Date(obl.due_date).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                    ZMW {parseFloat(obl.amount || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`px-2 py-1 text-xs font-semibold rounded-full ${getStatusColor(obl.status)}`}>
                      {obl.status}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            obl.compliance_percentage >= 90 ? 'bg-green-500' :
                            obl.compliance_percentage >= 70 ? 'bg-yellow-500' : 'bg-red-500'
                          }`}
                          style={{ width: `${obl.compliance_percentage}%` }}
                        />
                      </div>
                      <span className="text-sm font-medium">{obl.compliance_percentage}%</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm">
                    {obl.status === 'pending' && (
                      <button
                        onClick={() => updateObligation(obl.id, { status: 'submitted' })}
                        className="text-blue-600 hover:text-blue-800"
                      >
                        Mark Submitted
                      </button>
                    )}
                    {obl.status === 'submitted' && (
                      <button
                        onClick={() => updateObligation(obl.id, { status: 'paid' })}
                        className="text-green-600 hover:text-green-800"
                      >
                        Mark Paid
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {obligations.length === 0 && (
          <div className="text-center py-12 bg-white rounded-lg">
            <Calendar className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-600">No obligations found. Generate monthly obligations to get started.</p>
          </div>
        )}
      </div>
    </div>
  );
}
