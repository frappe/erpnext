import React, { useState } from 'react';
import { BarChart3, TrendingUp, DollarSign } from 'lucide-react';
import api from '../services/api';

function Reports() {
  const [reportType, setReportType] = useState('income_statement');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);

  const generateReport = async () => {
    setLoading(true);
    try {
      const response = await api.post('/api/reports/financial', {
        report_type: reportType,
        start_date: startDate,
        end_date: endDate
      });
      setReportData(response.data);
    } catch (error) {
      console.error('Error generating report:', error);
      alert('Failed to generate report');
    }
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold gradient-text">Financial Reports</h1>
      </div>

      <div className="glass-card p-6">
        <h2 className="text-xl font-semibold text-erik-primary mb-4">Generate Report</h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Report Type
            </label>
            <select
              value={reportType}
              onChange={(e) => setReportType(e.target.value)}
              className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
            >
              <option value="income_statement">Profit & Loss Statement</option>
              <option value="balance_sheet">Balance Sheet</option>
              <option value="cash_flow">Cash Flow Statement</option>
            </select>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Start Date
            </label>
            <input
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              End Date
            </label>
            <input
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              className="w-full bg-erik-dark border border-erik-primary/30 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-erik-primary"
            />
          </div>
          
          <div className="flex items-end">
            <button
              onClick={generateReport}
              disabled={loading}
              className="w-full bg-gradient-to-r from-erik-primary to-green-500 text-white px-6 py-2 rounded-lg font-semibold hover:shadow-lg hover:shadow-erik-primary/50 transition-all disabled:opacity-50"
            >
              {loading ? 'Generating...' : 'Generate'}
            </button>
          </div>
        </div>
      </div>

      {reportData && (
        <div className="glass-card p-6">
          <h2 className="text-2xl font-bold text-erik-primary mb-2">{reportData.report_type}</h2>
          <p className="text-gray-400 mb-6">{reportData.period}</p>

          {reportType === 'income_statement' && reportData.sections && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-green-400 mb-3">Revenue</h3>
                <div className="space-y-2">
                  {reportData.sections.revenue?.items?.map((item, idx) => (
                    <div key={idx} className="flex justify-between py-2 border-b border-gray-700">
                      <span className="text-gray-300">{item.code} - {item.name}</span>
                      <span className="text-white font-medium">K {item.amount.toLocaleString()}</span>
                    </div>
                  ))}
                  <div className="flex justify-between py-2 font-bold text-green-400">
                    <span>Total Revenue</span>
                    <span>K {reportData.sections.revenue?.total?.toLocaleString()}</span>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-red-400 mb-3">Expenses</h3>
                <div className="space-y-2">
                  {reportData.sections.expenses?.items?.map((item, idx) => (
                    <div key={idx} className="flex justify-between py-2 border-b border-gray-700">
                      <span className="text-gray-300">{item.code} - {item.name}</span>
                      <span className="text-white font-medium">K {item.amount.toLocaleString()}</span>
                    </div>
                  ))}
                  <div className="flex justify-between py-2 font-bold text-red-400">
                    <span>Total Expenses</span>
                    <span>K {reportData.sections.expenses?.total?.toLocaleString()}</span>
                  </div>
                </div>
              </div>

              <div className={`p-4 rounded-lg ${reportData.sections.net_income >= 0 ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
                <div className="flex justify-between items-center">
                  <span className="text-xl font-bold">Net Income</span>
                  <span className={`text-2xl font-bold ${reportData.sections.net_income >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                    K {reportData.sections.net_income?.toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          )}

          {reportType === 'balance_sheet' && reportData.sections && (
            <div className="space-y-6">
              <div>
                <h3 className="text-lg font-semibold text-erik-primary mb-3">Assets</h3>
                <div className="space-y-2">
                  {reportData.sections.assets?.items?.map((item, idx) => (
                    <div key={idx} className="flex justify-between py-2 border-b border-gray-700">
                      <span className="text-gray-300">{item.code} - {item.name}</span>
                      <span className="text-white font-medium">K {item.amount.toLocaleString()}</span>
                    </div>
                  ))}
                  <div className="flex justify-between py-2 font-bold text-erik-primary">
                    <span>Total Assets</span>
                    <span>K {reportData.sections.assets?.total?.toLocaleString()}</span>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-yellow-400 mb-3">Liabilities</h3>
                <div className="space-y-2">
                  {reportData.sections.liabilities?.items?.map((item, idx) => (
                    <div key={idx} className="flex justify-between py-2 border-b border-gray-700">
                      <span className="text-gray-300">{item.code} - {item.name}</span>
                      <span className="text-white font-medium">K {item.amount.toLocaleString()}</span>
                    </div>
                  ))}
                  <div className="flex justify-between py-2 font-bold text-yellow-400">
                    <span>Total Liabilities</span>
                    <span>K {reportData.sections.liabilities?.total?.toLocaleString()}</span>
                  </div>
                </div>
              </div>

              <div>
                <h3 className="text-lg font-semibold text-blue-400 mb-3">Equity</h3>
                <div className="space-y-2">
                  {reportData.sections.equity?.items?.map((item, idx) => (
                    <div key={idx} className="flex justify-between py-2 border-b border-gray-700">
                      <span className="text-gray-300">{item.code} - {item.name}</span>
                      <span className="text-white font-medium">K {item.amount.toLocaleString()}</span>
                    </div>
                  ))}
                  <div className="flex justify-between py-2 font-bold text-blue-400">
                    <span>Total Equity</span>
                    <span>K {reportData.sections.equity?.total?.toLocaleString()}</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default Reports;
