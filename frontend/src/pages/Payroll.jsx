import React, { useState, useEffect } from 'react';
import { DollarSign, Users, Calculator, FileText, Download } from 'lucide-react';
import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000';

function Payroll() {
  const [payruns, setPayruns] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [selectedPayrun, setSelectedPayrun] = useState(null);
  const [payslips, setPayslips] = useState([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState('list');
  
  const [newPayrun, setNewPayrun] = useState({
    year: new Date().getFullYear(),
    month: new Date().getMonth() + 1,
    pay_date: new Date().toISOString().split('T')[0]
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const [payrunsRes, employeesRes] = await Promise.all([
        axios.get(`${API_URL}/api/payroll/payruns`, { headers }),
        axios.get(`${API_URL}/api/employees/`, { headers })
      ]);

      setPayruns(payrunsRes.data.payruns || []);
      setEmployees(employeesRes.data.employees || []);
      setLoading(false);
    } catch (error) {
      console.error('Error loading payroll data:', error);
      setLoading(false);
    }
  };

  const createPayrun = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(
        `${API_URL}/api/payroll/payruns`,
        newPayrun,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      alert('Payrun created successfully!');
      setView('list');
      loadData();
    } catch (error) {
      alert('Error creating payrun: ' + (error.response?.data?.detail || error.message));
    }
  };

  const calculatePayrun = async (payrunId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_URL}/api/payroll/payruns/${payrunId}/calculate`,
        {},
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      alert(`Payrun calculated! ${response.data.payslips_created} payslips created.`);
      loadData();
    } catch (error) {
      alert('Error calculating payrun: ' + (error.response?.data?.detail || error.message));
    }
  };

  const viewPayrun = async (payrun) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(
        `${API_URL}/api/payroll/payruns/${payrun.id}`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      
      setSelectedPayrun(response.data.payrun);
      setPayslips(response.data.payslips || []);
      setView('view');
    } catch (error) {
      alert('Error loading payrun details: ' + (error.response?.data?.detail || error.message));
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      draft: 'bg-yellow-500/20 text-yellow-400',
      calculated: 'bg-blue-500/20 text-blue-400',
      approved: 'bg-green-500/20 text-green-400',
      paid: 'bg-purple-500/20 text-purple-400'
    };
    return colors[status] || 'bg-gray-500/20 text-gray-400';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-xl text-erik-primary">Loading payroll data...</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold gradient-text">Payroll Management</h1>
          <p className="text-gray-400 mt-1">Zambian 2025 Compliance (PAYE, NAPSA, NHIMA)</p>
        </div>
        
        {view === 'list' && (
          <button
            onClick={() => setView('create')}
            className="bg-gradient-to-r from-erik-primary to-green-500 text-white px-6 py-2 rounded-lg font-semibold hover:shadow-lg hover:shadow-erik-primary/50 transition-all flex items-center gap-2"
          >
            <DollarSign size={20} />
            Create Payrun
          </button>
        )}
        
        {view !== 'list' && (
          <button
            onClick={() => { setView('list'); loadData(); }}
            className="bg-gray-700 text-white px-6 py-2 rounded-lg font-semibold hover:bg-gray-600 transition-all"
          >
            Back to List
          </button>
        )}
      </div>

      {view === 'create' && (
        <div className="glass-card p-6">
          <h2 className="text-xl font-semibold text-erik-primary mb-6">Create New Payrun</h2>
          
          <div className="grid grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Year</label>
              <select
                value={newPayrun.year}
                onChange={(e) => setNewPayrun({ ...newPayrun, year: parseInt(e.target.value) })}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              >
                {[2024, 2025, 2026].map((year) => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Month</label>
              <select
                value={newPayrun.month}
                onChange={(e) => setNewPayrun({ ...newPayrun, month: parseInt(e.target.value) })}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              >
                {[...Array(12)].map((_, i) => (
                  <option key={i} value={i + 1}>
                    {new Date(2000, i).toLocaleString('default', { month: 'long' })}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">Pay Date</label>
              <input
                type="date"
                value={newPayrun.pay_date}
                onChange={(e) => setNewPayrun({ ...newPayrun, pay_date: e.target.value })}
                className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
              />
            </div>

            <div className="flex items-end">
              <button
                onClick={createPayrun}
                className="w-full bg-gradient-to-r from-erik-primary to-green-500 text-white px-6 py-2 rounded-lg font-semibold hover:shadow-lg hover:shadow-erik-primary/50 transition-all"
              >
                Create Payrun
              </button>
            </div>
          </div>

          <div className="mt-6 p-4 bg-blue-500/10 rounded-lg border border-blue-500/30">
            <p className="text-sm text-blue-400">
              <strong>Note:</strong> Creating a payrun for {employees.length} active employees. 
              Calculate it to generate payslips with PAYE, NAPSA, and NHIMA deductions.
            </p>
          </div>
        </div>
      )}

      {view === 'view' && selectedPayrun && (
        <div className="space-y-6">
          <div className="glass-card p-6">
            <div className="flex justify-between items-start mb-6">
              <div>
                <h2 className="text-2xl font-bold text-erik-primary">
                  Payrun: {selectedPayrun.year}-{String(selectedPayrun.month).padStart(2, '0')}
                </h2>
                <p className="text-gray-400">Pay Date: {new Date(selectedPayrun.pay_date).toLocaleDateString()}</p>
              </div>
              <span className={`px-3 py-1 rounded-full text-sm font-semibold ${getStatusColor(selectedPayrun.status)}`}>
                {selectedPayrun.status}
              </span>
            </div>

            <div className="grid grid-cols-4 gap-6">
              <div className="bg-erik-dark/50 rounded-lg p-4 border border-erik-primary/20">
                <p className="text-sm text-gray-400">Total Gross</p>
                <p className="text-2xl font-bold text-white mt-1">
                  K {parseFloat(selectedPayrun.total_gross || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </p>
              </div>
              <div className="bg-erik-dark/50 rounded-lg p-4 border border-red-500/20">
                <p className="text-sm text-gray-400">Total Deductions</p>
                <p className="text-2xl font-bold text-red-400 mt-1">
                  K {parseFloat(selectedPayrun.total_deductions || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </p>
              </div>
              <div className="bg-erik-dark/50 rounded-lg p-4 border border-green-500/20">
                <p className="text-sm text-gray-400">Total Net</p>
                <p className="text-2xl font-bold text-green-400 mt-1">
                  K {parseFloat(selectedPayrun.total_net || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                </p>
              </div>
              <div className="bg-erik-dark/50 rounded-lg p-4 border border-blue-500/20">
                <p className="text-sm text-gray-400">Employees</p>
                <p className="text-2xl font-bold text-blue-400 mt-1">{payslips.length}</p>
              </div>
            </div>
          </div>

          <div className="glass-card overflow-hidden">
            <div className="px-6 py-4 bg-erik-primary/10 border-b border-erik-primary/30">
              <h3 className="text-lg font-bold text-erik-primary">Employee Payslips</h3>
            </div>
            <table className="w-full">
              <thead className="bg-erik-dark/50 border-b border-erik-primary/30">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase">Employee</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase">Gross</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase">PAYE</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase">NAPSA</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase">NHIMA</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase">Net Pay</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {payslips.map((slip) => (
                  <tr key={slip.id} className="hover:bg-erik-dark/50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="font-medium text-white">{slip.employee_name || 'Employee'}</div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                      K {parseFloat(slip.gross_pay || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-red-400">
                      K {parseFloat(slip.paye || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-red-400">
                      K {parseFloat(slip.napsa_employee || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-red-400">
                      K {parseFloat(slip.nhima_employee || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-green-400">
                      K {parseFloat(slip.net_pay || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {view === 'list' && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="glass-card p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Active Employees</p>
                  <p className="text-3xl font-bold text-erik-primary mt-1">{employees.length}</p>
                </div>
                <Users className="text-erik-primary" size={40} />
              </div>
            </div>

            <div className="glass-card p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">Total Payruns</p>
                  <p className="text-3xl font-bold text-green-400 mt-1">{payruns.length}</p>
                </div>
                <Calculator className="text-green-400" size={40} />
              </div>
            </div>

            <div className="glass-card p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm">This Month</p>
                  <p className="text-3xl font-bold text-purple-400 mt-1">
                    {payruns.filter(p => 
                      p.year === new Date().getFullYear() && 
                      p.month === new Date().getMonth() + 1
                    ).length}
                  </p>
                </div>
                <DollarSign className="text-purple-400" size={40} />
              </div>
            </div>
          </div>

          <div className="glass-card overflow-hidden">
            <table className="w-full">
              <thead className="bg-erik-primary/10 border-b border-erik-primary/30">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase">Period</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase">Pay Date</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase">Total Gross</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase">Total Net</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-erik-primary uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-700">
                {payruns.map((payrun) => (
                  <tr key={payrun.id} className="hover:bg-erik-dark/50 transition-colors">
                    <td className="px-6 py-4 whitespace-nowrap">
                      <div className="font-medium text-white">
                        {payrun.year}-{String(payrun.month).padStart(2, '0')}
                      </div>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                      {new Date(payrun.pay_date).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-300">
                      K {parseFloat(payrun.total_gross || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-green-400">
                      K {parseFloat(payrun.total_net || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getStatusColor(payrun.status)}`}>
                        {payrun.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm space-x-2">
                      <button
                        onClick={() => viewPayrun(payrun)}
                        className="text-blue-400 hover:text-blue-300"
                      >
                        View
                      </button>
                      {payrun.status === 'draft' && (
                        <button
                          onClick={() => calculatePayrun(payrun.id)}
                          className="text-green-400 hover:text-green-300"
                        >
                          Calculate
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {payruns.length === 0 && (
            <div className="text-center py-12 glass-card">
              <DollarSign className="w-16 h-16 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">No payruns found. Create your first payrun to get started.</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}

export default Payroll;
