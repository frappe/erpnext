import { useState, useEffect } from 'react';
import { Receipt, TrendingUp, FileText, Calendar } from 'lucide-react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function TaxDashboard() {
  const [taxSettings, setTaxSettings] = useState([]);
  const [vatReturn, setVatReturn] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      const today = new Date();
      const startDate = new Date(today.getFullYear(), today.getMonth(), 1).toISOString().split('T')[0];
      const endDate = today.toISOString().split('T')[0];

      const [settingsRes, vatRes] = await Promise.all([
        axios.get(`${API_URL}/api/tax/settings`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_URL}/api/tax/vat-return?start_date=${startDate}&end_date=${endDate}`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);
      setTaxSettings(settingsRes.data);
      setVatReturn(vatRes.data);
    } catch (error) {
      console.error('Error fetching tax data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getTaxTypeColor = (type) => {
    const colors = {
      vat: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      paye: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      withholding_tax: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
      turnover_tax: 'bg-green-500/20 text-green-400 border-green-500/30',
      excise: 'bg-red-500/20 text-red-400 border-red-500/30'
    };
    return colors[type] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-teal-900 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Tax & VAT Dashboard</h1>
          <p className="text-gray-400">Manage tax settings and generate VAT returns</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-gradient-to-br from-blue-500/20 to-purple-500/20 backdrop-blur-sm rounded-lg p-6 border border-blue-500/30">
            <div className="flex items-center justify-between mb-2">
              <Receipt className="w-8 h-8 text-blue-400" />
              <span className="text-xs text-blue-300 font-medium">OUTPUT VAT</span>
            </div>
            <p className="text-3xl font-bold text-white">
              ZMW {vatReturn?.output_vat?.toLocaleString() || 0}
            </p>
            <p className="text-sm text-gray-400 mt-1">Sales VAT collected</p>
          </div>

          <div className="bg-gradient-to-br from-green-500/20 to-teal-500/20 backdrop-blur-sm rounded-lg p-6 border border-green-500/30">
            <div className="flex items-center justify-between mb-2">
              <TrendingUp className="w-8 h-8 text-green-400" />
              <span className="text-xs text-green-300 font-medium">INPUT VAT</span>
            </div>
            <p className="text-3xl font-bold text-white">
              ZMW {vatReturn?.input_vat?.toLocaleString() || 0}
            </p>
            <p className="text-sm text-gray-400 mt-1">Purchase VAT paid</p>
          </div>

          <div className="bg-gradient-to-br from-orange-500/20 to-red-500/20 backdrop-blur-sm rounded-lg p-6 border border-orange-500/30">
            <div className="flex items-center justify-between mb-2">
              <FileText className="w-8 h-8 text-orange-400" />
              <span className="text-xs text-orange-300 font-medium">NET PAYABLE</span>
            </div>
            <p className="text-3xl font-bold text-white">
              ZMW {vatReturn?.net_vat?.toLocaleString() || 0}
            </p>
            <p className="text-sm text-gray-400 mt-1">VAT to pay/refund</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
            <h2 className="text-xl font-bold text-white mb-4">Active Tax Settings</h2>
            <div className="space-y-3">
              {taxSettings.filter(tax => tax.is_active).map((tax) => (
                <div key={tax.id} className={`rounded-lg p-4 border ${getTaxTypeColor(tax.tax_type)}`}>
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <h3 className="font-semibold text-white">{tax.tax_name}</h3>
                      <p className="text-xs text-gray-400">{tax.tax_type?.replace('_', ' ').toUpperCase()}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-2xl font-bold">{tax.rate}%</p>
                    </div>
                  </div>
                  {tax.description && (
                    <p className="text-sm text-gray-400 mt-2">{tax.description}</p>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
            <h2 className="text-xl font-bold text-white mb-4">VAT Return - Current Month</h2>
            {vatReturn ? (
              <div className="space-y-4">
                <div className="bg-gray-900/50 rounded-lg p-4">
                  <div className="flex items-center gap-3 mb-3">
                    <Calendar className="w-5 h-5 text-teal-400" />
                    <span className="text-gray-400">Period</span>
                  </div>
                  <p className="text-white font-semibold">
                    {vatReturn.start_date} to {vatReturn.end_date}
                  </p>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between items-center p-3 bg-blue-500/10 rounded-lg border border-blue-500/20">
                    <span className="text-gray-300">Output VAT (Sales)</span>
                    <span className="font-semibold text-blue-400">
                      ZMW {vatReturn.output_vat?.toLocaleString()}
                    </span>
                  </div>

                  <div className="flex justify-between items-center p-3 bg-green-500/10 rounded-lg border border-green-500/20">
                    <span className="text-gray-300">Input VAT (Purchases)</span>
                    <span className="font-semibold text-green-400">
                      ZMW {vatReturn.input_vat?.toLocaleString()}
                    </span>
                  </div>

                  <div className="flex justify-between items-center p-3 bg-orange-500/10 rounded-lg border border-orange-500/20">
                    <span className="text-gray-300 font-medium">Net VAT Payable</span>
                    <span className="font-bold text-xl text-orange-400">
                      ZMW {vatReturn.net_vat?.toLocaleString()}
                    </span>
                  </div>
                </div>

                <div className="mt-6">
                  <button className="w-full px-6 py-3 bg-gradient-to-r from-teal-500 to-green-500 text-white rounded-lg hover:from-teal-600 hover:to-green-600 transition-all font-semibold">
                    Generate VAT Return Report
                  </button>
                </div>
              </div>
            ) : (
              <div className="text-center py-12">
                <FileText className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                <p className="text-gray-400">No VAT data for current period</p>
              </div>
            )}
          </div>
        </div>

        <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
          <h2 className="text-xl font-bold text-white mb-4">All Tax Settings</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Tax Name</th>
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Type</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Rate</th>
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Description</th>
                  <th className="text-center py-3 px-4 text-gray-400 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {taxSettings.map((tax) => (
                  <tr key={tax.id} className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                    <td className="py-3 px-4 text-white font-medium">{tax.tax_name}</td>
                    <td className="py-3 px-4">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${getTaxTypeColor(tax.tax_type)}`}>
                        {tax.tax_type?.replace('_', ' ').toUpperCase()}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right font-semibold text-white">{tax.rate}%</td>
                    <td className="py-3 px-4 text-gray-300">{tax.description || 'N/A'}</td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                        tax.is_active ? 'bg-green-500/20 text-green-400' : 'bg-gray-500/20 text-gray-400'
                      }`}>
                        {tax.is_active ? 'ACTIVE' : 'INACTIVE'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
