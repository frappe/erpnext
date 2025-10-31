import React, { useState, useEffect } from 'react';
import { DollarSign, Plus } from 'lucide-react';
import api from '../services/api';

function Payroll() {
  const [payslips, setPayslips] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    employee_id: '',
    period_month: new Date().getMonth() + 1,
    period_year: new Date().getFullYear()
  });

  useEffect(() => {
    fetchPayslips();
    fetchEmployees();
  }, []);

  const fetchPayslips = async () => {
    try {
      const response = await api.get('/api/payslips');
      setPayslips(response.data);
    } catch (error) {
      console.error('Error fetching payslips:', error);
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await api.post('/api/payslips', formData);
      setShowForm(false);
      setFormData({
        employee_id: '',
        period_month: new Date().getMonth() + 1,
        period_year: new Date().getFullYear()
      });
      fetchPayslips();
      alert('Payslip generated successfully with Zambian tax calculations (PAYE, NAPSA, NHIMA)!');
    } catch (error) {
      console.error('Error creating payslip:', error);
      alert('Failed to create payslip');
    }
  };

  const months = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December'
  ];

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold gradient-text">Payroll Management</h1>
        <button
          onClick={() => setShowForm(!showForm)}
          className="bg-gradient-to-r from-erik-primary to-green-500 text-white px-6 py-2 rounded-lg font-semibold hover:shadow-lg hover:shadow-erik-primary/50 transition-all flex items-center gap-2"
        >
          <Plus size={20} />
          Generate Payslip
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="glass-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Total Payslips</p>
              <p className="text-2xl font-bold text-erik-primary mt-1">{payslips.length}</p>
            </div>
            <DollarSign className="text-erik-primary" size={32} />
          </div>
        </div>
        <div className="glass-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Zambian Compliance</p>
              <p className="text-lg font-bold text-green-400 mt-1">PAYE + NAPSA + NHIMA</p>
            </div>
          </div>
        </div>
        <div className="glass-card p-6">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-gray-400 text-sm">Auto Calculations</p>
              <p className="text-lg font-bold text-erik-primary mt-1">Tax Brackets & Deductions</p>
            </div>
          </div>
        </div>
      </div>

      {showForm && (
        <div className="glass-card p-6">
          <h2 className="text-xl font-semibold text-erik-primary mb-4">Generate Payslip</h2>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 md:grid-cols-3 gap-4">
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
              <label className="block text-sm font-medium text-gray-300 mb-2">Month</label>
              <select
                value={formData.period_month}
                onChange={(e) => setFormData({...formData, period_month: parseInt(e.target.value)})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              >
                {months.map((month, idx) => (
                  <option key={idx} value={idx + 1}>{month}</option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Year</label>
              <input
                type="number"
                value={formData.period_year}
                onChange={(e) => setFormData({...formData, period_year: parseInt(e.target.value)})}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              />
            </div>
            <div className="md:col-span-3 flex gap-4">
              <button
                type="submit"
                className="bg-gradient-to-r from-erik-primary to-green-500 text-white px-6 py-2 rounded-lg font-semibold hover:shadow-lg hover:shadow-erik-primary/50 transition-all"
              >
                Generate Payslip (with PAYE, NAPSA, NHIMA)
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
              <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase tracking-wider">Payslip #</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase tracking-wider">Period</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase tracking-wider">Gross</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase tracking-wider">Net</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase tracking-wider">Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-700">
            {payslips.map((payslip) => (
              <tr key={payslip.id} className="hover:bg-erik-dark/50 transition-colors">
                <td className="px-6 py-4 whitespace-nowrap text-sm text-erik-primary font-medium">{payslip.payslip_number}</td>
                <td className="px-6 py-4 text-sm text-gray-300">{months[payslip.period_month - 1]} {payslip.period_year}</td>
                <td className="px-6 py-4 text-sm text-white">K {payslip.gross_salary.toFixed(2)}</td>
                <td className="px-6 py-4 text-sm text-green-400 font-medium">K {payslip.net_salary.toFixed(2)}</td>
                <td className="px-6 py-4 text-sm">
                  <span className={`px-2 py-1 rounded-full text-xs ${
                    payslip.status === 'draft' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-green-500/20 text-green-400'
                  }`}>
                    {payslip.status}
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

export default Payroll;
