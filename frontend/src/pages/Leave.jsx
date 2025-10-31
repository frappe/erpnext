import React, { useState, useEffect } from 'react';
import { Calendar, Plus } from 'lucide-react';
import api from '../services/api';

function Leave() {
  const [applications, setApplications] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [leaveTypes, setLeaveTypes] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    employee_id: '',
    leave_type_id: '',
    start_date: '',
    end_date: '',
    days_requested: 1,
    reason: ''
  });

  useEffect(() => {
    fetchApplications();
    fetchEmployees();
    fetchLeaveTypes();
  }, []);

  const fetchApplications = async () => {
    try {
      const response = await api.get('/api/leave-applications');
      setApplications(response.data);
    } catch (error) {
      console.error('Error fetching applications:', error);
    }
  };

  const fetchEmployees = async () => {
    try {
      const response = await api.get('/api/employees');
      setEmployees(response.data);
    } catch (error) {
      console.error('Error fetching employees:', error);
    }
  };

  const fetchLeaveTypes = async () => {
    try {
      const response = await api.get('/api/leave-types');
      setLeaveTypes(response.data);
    } catch (error) {
      console.error('Error fetching leave types:', error);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.post('/api/leave-applications', formData);
      setShowForm(false);
      setFormData({
        employee_id: '',
        leave_type_id: '',
        start_date: '',
        end_date: '',
        days_requested: 1,
        reason: ''
      });
      fetchApplications();
    } catch (error) {
      console.error('Error creating application:', error);
      alert('Failed to create leave application');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold gradient-text">Leave Management</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-gradient-to-r from-erik-primary to-green-500 text-white px-6 py-2 rounded-lg font-semibold hover:shadow-lg hover:shadow-erik-primary/50 transition-all flex items-center gap-2"
        >
          <Plus size={20} />
          New Application
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Total Applications</p>
              <p className="text-2xl font-bold text-erik-primary mt-1">{applications.length}</p>
            </div>
            <Calendar className="text-erik-primary" size={32} />
          </div>
        </div>
        <div className="glass-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Pending</p>
              <p className="text-2xl font-bold text-yellow-400 mt-1">
                {applications.filter(a => a.status === 'pending').length}
              </p>
            </div>
          </div>
        </div>
        <div className="glass-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Approved</p>
              <p className="text-2xl font-bold text-green-400 mt-1">
                {applications.filter(a => a.status === 'approved').length}
              </p>
            </div>
          </div>
        </div>
      </div>

      {showForm && (
        <div className="glass-card p-6">
          <h2 className="text-xl font-semibold text-erik-primary mb-4">New Leave Application</h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Employee</label>
              <select
                required
                value={formData.employee_id}
                onChange={(e) => setFormData({...formData, employee_id: e.target.value})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              >
                <option value="">Select Employee</option>
                {employees.map((emp) => (
                  <option key={emp.id} value={emp.id}>
                    {emp.first_name} {emp.last_name} - {emp.employee_no}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Leave Type</label>
              <select
                required
                value={formData.leave_type_id}
                onChange={(e) => setFormData({...formData, leave_type_id: e.target.value})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              >
                <option value="">Select Leave Type</option>
                {leaveTypes.map((type) => (
                  <option key={type.id} value={type.id}>{type.name} ({type.code})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Start Date</label>
              <input
                type="date"
                required
                value={formData.start_date}
                onChange={(e) => setFormData({...formData, start_date: e.target.value})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">End Date</label>
              <input
                type="date"
                required
                value={formData.end_date}
                onChange={(e) => setFormData({...formData, end_date: e.target.value})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Days Requested</label>
              <input
                type="number"
                required
                step="0.5"
                value={formData.days_requested}
                onChange={(e) => setFormData({...formData, days_requested: parseFloat(e.target.value)})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-300 mb-2">Reason</label>
              <textarea
                value={formData.reason}
                onChange={(e) => setFormData({...formData, reason: e.target.value})}
                rows="3"
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              />
            </div>
            <div className="md:col-span-2 flex gap-4">
              <button
                type="submit"
                className="bg-gradient-to-r from-erik-primary to-green-500 text-white px-6 py-2 rounded-lg font-semibold hover:shadow-lg hover:shadow-erik-primary/50 transition-all"
              >
                Submit Application
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
              <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase tracking-wider">Application #</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase tracking-wider">Period</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase tracking-wider">Days</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {applications.map((app) => (
              <tr key={app.id} className="hover:bg-erik-dark/50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-erik-primary font-medium">{app.application_number}</td>
                <td className="px-6 py-4 text-sm text-gray-300">{app.start_date} to {app.end_date}</td>
                <td className="px-6 py-4 text-sm text-white">{app.days_requested} days</td>
                <td className="px-6 py-4 text-sm">
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    app.status === 'pending' ? 'bg-yellow-500/20 text-yellow-400' :
                    app.status === 'approved' ? 'bg-green-500/20 text-green-400' :
                    'bg-red-500/20 text-red-400'
                  }`}>
                    {app.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default Leave;
