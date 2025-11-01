import { useState } from 'react';
import { BarChart3, Building2, Download } from 'lucide-react';
import axios from 'axios';

export default function ConsolidatedReports() {
  const [reportType, setReportType] = useState('pl');
  const [groupBy, setGroupBy] = useState('department');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');
  const [asOfDate, setAsOfDate] = useState('');
  const [reportData, setReportData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const fetchReport = async () => {
    setError('');
    setLoading(true);

    try {
      const token = localStorage.getItem('token');
      const config = {
        headers: { Authorization: `Bearer ${token}` },
        params: { group_by: groupBy }
      };

      let response;
      if (reportType === 'pl') {
        if (!startDate || !endDate) {
          setError('Please select start and end dates');
          setLoading(false);
          return;
        }
        config.params.start_date = startDate;
        config.params.end_date = endDate;
        response = await axios.get('/api/reports/consolidated-pl', config);
      } else {
        if (!asOfDate) {
          setError('Please select as-of date');
          setLoading(false);
          return;
        }
        config.params.as_of_date = asOfDate;
        response = await axios.get('/api/reports/consolidated-balance-sheet', config);
      }

      setReportData(response.data);
    } catch (error) {
      console.error('Error fetching report:', error);
      setError(error.response?.data?.detail || 'Failed to generate report');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-ZM', {
      style: 'currency',
      currency: 'ZMW'
    }).format(amount || 0);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-teal-900 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center gap-3 mb-8">
          <BarChart3 className="text-teal-400" size={32} />
          <h1 className="text-3xl font-bold text-white">Consolidated Reports</h1>
        </div>

        {/* Report Filters */}
        <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-lg p-6 mb-8">
          <div className="grid grid-cols-4 gap-4 mb-4">
            <div>
              <label className="block text-gray-300 mb-2">Report Type</label>
              <select
                value={reportType}
                onChange={(e) => setReportType(e.target.value)}
                className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600 focus:outline-none focus:border-teal-400"
              >
                <option value="pl">Profit & Loss</option>
                <option value="bs">Balance Sheet</option>
              </select>
            </div>
            <div>
              <label className="block text-gray-300 mb-2">Group By</label>
              <select
                value={groupBy}
                onChange={(e) => setGroupBy(e.target.value)}
                className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600 focus:outline-none focus:border-teal-400"
              >
                <option value="department">Department</option>
                <option value="branch">Branch</option>
                <option value="company">Company Total</option>
              </select>
            </div>
            {reportType === 'pl' ? (
              <>
                <div>
                  <label className="block text-gray-300 mb-2">Start Date</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600 focus:outline-none focus:border-teal-400"
                  />
                </div>
                <div>
                  <label className="block text-gray-300 mb-2">End Date</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600 focus:outline-none focus:border-teal-400"
                  />
                </div>
              </>
            ) : (
              <div className="col-span-2">
                <label className="block text-gray-300 mb-2">As Of Date</label>
                <input
                  type="date"
                  value={asOfDate}
                  onChange={(e) => setAsOfDate(e.target.value)}
                  className="w-full bg-gray-700 text-white px-4 py-2 rounded-lg border border-gray-600 focus:outline-none focus:border-teal-400"
                />
              </div>
            )}
          </div>
          <button
            onClick={fetchReport}
            disabled={loading}
            className="flex items-center gap-2 bg-teal-500 hover:bg-teal-600 disabled:bg-gray-600 text-white px-6 py-2 rounded-lg transition-colors"
          >
            <BarChart3 size={20} />
            {loading ? 'Generating...' : 'Generate Report'}
          </button>
        </div>

        {error && (
          <div className="bg-red-500/20 border border-red-500 text-red-200 px-4 py-3 rounded-lg mb-6">
            {error}
          </div>
        )}

        {/* Report Display */}
        {reportData && (
          <div className="space-y-6">
            {reportType === 'pl' ? (
              // Profit & Loss Report
              Object.entries(reportData.report_data).map(([groupKey, data]) => (
                <div key={groupKey} className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-lg p-6">
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                      <Building2 size={24} className="text-teal-400" />
                      {groupKey}
                    </h2>
                    <span className={`text-xl font-bold ${
                      data.net_profit >= 0 ? 'text-green-400' : 'text-red-400'
                    }`}>
                      Net Profit: {formatCurrency(data.net_profit)}
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-6">
                    {/* Income Section */}
                    <div>
                      <h3 className="text-lg font-semibold text-teal-400 mb-3">Income</h3>
                      {Object.entries(data.income).length > 0 ? (
                        <div className="space-y-2">
                          {Object.entries(data.income).map(([account, amount]) => (
                            <div key={account} className="flex justify-between text-gray-300">
                              <span>{account}</span>
                              <span className="font-mono">{formatCurrency(amount)}</span>
                            </div>
                          ))}
                          <div className="border-t border-gray-600 pt-2 mt-2 flex justify-between text-white font-bold">
                            <span>Total Income</span>
                            <span className="font-mono">{formatCurrency(data.total_income)}</span>
                          </div>
                        </div>
                      ) : (
                        <p className="text-gray-500">No income recorded</p>
                      )}
                    </div>

                    {/* Expenses Section */}
                    <div>
                      <h3 className="text-lg font-semibold text-teal-400 mb-3">Expenses</h3>
                      {Object.entries(data.expenses).length > 0 ? (
                        <div className="space-y-2">
                          {Object.entries(data.expenses).map(([account, amount]) => (
                            <div key={account} className="flex justify-between text-gray-300">
                              <span>{account}</span>
                              <span className="font-mono">{formatCurrency(amount)}</span>
                            </div>
                          ))}
                          <div className="border-t border-gray-600 pt-2 mt-2 flex justify-between text-white font-bold">
                            <span>Total Expenses</span>
                            <span className="font-mono">{formatCurrency(data.total_expenses)}</span>
                          </div>
                        </div>
                      ) : (
                        <p className="text-gray-500">No expenses recorded</p>
                      )}
                    </div>
                  </div>
                </div>
              ))
            ) : (
              // Balance Sheet Report
              Object.entries(reportData.report_data).map(([groupKey, data]) => (
                <div key={groupKey} className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-lg p-6">
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                      <Building2 size={24} className="text-teal-400" />
                      {groupKey}
                    </h2>
                  </div>

                  <div className="grid grid-cols-3 gap-6">
                    {/* Assets */}
                    <div>
                      <h3 className="text-lg font-semibold text-teal-400 mb-3">Assets</h3>
                      {Object.entries(data.assets).length > 0 ? (
                        <div className="space-y-2">
                          {Object.entries(data.assets).map(([account, amount]) => (
                            <div key={account} className="flex justify-between text-gray-300">
                              <span className="text-sm">{account}</span>
                              <span className="font-mono text-sm">{formatCurrency(amount)}</span>
                            </div>
                          ))}
                          <div className="border-t border-gray-600 pt-2 mt-2 flex justify-between text-white font-bold">
                            <span>Total</span>
                            <span className="font-mono">{formatCurrency(data.total_assets)}</span>
                          </div>
                        </div>
                      ) : (
                        <p className="text-gray-500 text-sm">No assets</p>
                      )}
                    </div>

                    {/* Liabilities */}
                    <div>
                      <h3 className="text-lg font-semibold text-teal-400 mb-3">Liabilities</h3>
                      {Object.entries(data.liabilities).length > 0 ? (
                        <div className="space-y-2">
                          {Object.entries(data.liabilities).map(([account, amount]) => (
                            <div key={account} className="flex justify-between text-gray-300">
                              <span className="text-sm">{account}</span>
                              <span className="font-mono text-sm">{formatCurrency(amount)}</span>
                            </div>
                          ))}
                          <div className="border-t border-gray-600 pt-2 mt-2 flex justify-between text-white font-bold">
                            <span>Total</span>
                            <span className="font-mono">{formatCurrency(data.total_liabilities)}</span>
                          </div>
                        </div>
                      ) : (
                        <p className="text-gray-500 text-sm">No liabilities</p>
                      )}
                    </div>

                    {/* Equity */}
                    <div>
                      <h3 className="text-lg font-semibold text-teal-400 mb-3">Equity</h3>
                      {Object.entries(data.equity).length > 0 ? (
                        <div className="space-y-2">
                          {Object.entries(data.equity).map(([account, amount]) => (
                            <div key={account} className="flex justify-between text-gray-300">
                              <span className="text-sm">{account}</span>
                              <span className="font-mono text-sm">{formatCurrency(amount)}</span>
                            </div>
                          ))}
                          <div className="border-t border-gray-600 pt-2 mt-2 flex justify-between text-white font-bold">
                            <span>Total</span>
                            <span className="font-mono">{formatCurrency(data.total_equity)}</span>
                          </div>
                        </div>
                      ) : (
                        <p className="text-gray-500 text-sm">No equity</p>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {!reportData && !loading && (
          <div className="bg-gray-800/50 backdrop-blur-sm border border-gray-700 rounded-lg p-12 text-center">
            <BarChart3 className="mx-auto text-gray-600 mb-4" size={64} />
            <p className="text-gray-400 text-lg">
              Select report parameters and click "Generate Report" to view consolidated financial reports.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
