import { useState, useEffect } from 'react';
import { Search, Download, Filter, Eye, Activity, Shield, AlertTriangle, CheckCircle, XCircle } from 'lucide-react';
import axios from 'axios';

export default function AuditTrail() {
  const [logs, setLogs] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    start_date: '',
    end_date: '',
    user_id: '',
    action: '',
    entity_type: '',
    status: ''
  });
  const [searchTerm, setSearchTerm] = useState('');
  const [showFilters, setShowFilters] = useState(false);

  const token = localStorage.getItem('token');
  const config = { headers: { Authorization: `Bearer ${token}` } };

  useEffect(() => {
    fetchLogs();
    fetchStats();
  }, []);

  const fetchLogs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.user_id) params.append('user_id', filters.user_id);
      if (filters.action) params.append('action', filters.action);
      if (filters.entity_type) params.append('entity_type', filters.entity_type);
      if (filters.status) params.append('status', filters.status);

      const response = await axios.get(`/api/audit-logs?${params.toString()}`, config);
      setLogs(response.data);
    } catch (error) {
      console.error('Failed to fetch audit logs:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await axios.get('/api/audit-logs/stats', config);
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch audit stats:', error);
    }
  };

  const handleFilterChange = (key, value) => {
    setFilters(prev => ({ ...prev, [key]: value }));
  };

  const handleApplyFilters = () => {
    fetchLogs();
    fetchStats();
  };

  const handleClearFilters = () => {
    setFilters({
      start_date: '',
      end_date: '',
      user_id: '',
      action: '',
      entity_type: '',
      status: ''
    });
    setSearchTerm('');
  };

  const handleExport = async () => {
    try {
      const params = new URLSearchParams();
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.action) params.append('action', filters.action);
      if (filters.entity_type) params.append('entity_type', filters.entity_type);

      const response = await axios.post(`/api/audit-logs/export?${params.toString()}`, {}, {
        ...config,
        responseType: 'blob'
      });

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `audit_logs_${new Date().toISOString()}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
    } catch (error) {
      console.error('Failed to export audit logs:', error);
    }
  };

  const getActionIcon = (action) => {
    switch (action) {
      case 'CREATE': return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'UPDATE': return <Activity className="w-4 h-4 text-blue-400" />;
      case 'DELETE': return <XCircle className="w-4 h-4 text-red-400" />;
      case 'READ': return <Eye className="w-4 h-4 text-gray-400" />;
      case 'LOGIN': return <Shield className="w-4 h-4 text-green-400" />;
      case 'LOGOUT': return <Shield className="w-4 h-4 text-gray-400" />;
      case 'EXPORT': return <Download className="w-4 h-4 text-purple-400" />;
      default: return <Activity className="w-4 h-4 text-gray-400" />;
    }
  };

  const getActionColor = (action) => {
    switch (action) {
      case 'CREATE': return 'bg-green-400/10 text-green-400 border-green-400/20';
      case 'UPDATE': return 'bg-blue-400/10 text-blue-400 border-blue-400/20';
      case 'DELETE': return 'bg-red-400/10 text-red-400 border-red-400/20';
      case 'READ': return 'bg-gray-400/10 text-gray-400 border-gray-400/20';
      case 'LOGIN': return 'bg-green-400/10 text-green-400 border-green-400/20';
      case 'LOGOUT': return 'bg-gray-400/10 text-gray-400 border-gray-400/20';
      case 'EXPORT': return 'bg-purple-400/10 text-purple-400 border-purple-400/20';
      default: return 'bg-gray-400/10 text-gray-400 border-gray-400/20';
    }
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'success':
        return <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs bg-green-400/10 text-green-400 border border-green-400/20">
          <CheckCircle className="w-3 h-3" /> Success
        </span>;
      case 'failure':
        return <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs bg-red-400/10 text-red-400 border border-red-400/20">
          <XCircle className="w-3 h-3" /> Failure
        </span>;
      case 'error':
        return <span className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs bg-orange-400/10 text-orange-400 border border-orange-400/20">
          <AlertTriangle className="w-3 h-3" /> Error
        </span>;
      default:
        return <span className="px-2 py-1 rounded text-xs bg-gray-400/10 text-gray-400 border border-gray-400/20">{status}</span>;
    }
  };

  const filteredLogs = logs.filter(log =>
    searchTerm === '' ||
    log.action?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    log.user_email?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    log.entity_type?.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Audit Trail</h1>
          <p className="text-gray-400">Complete system activity log for compliance and security</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white hover:bg-white/10 transition-colors flex items-center gap-2"
          >
            <Filter className="w-4 h-4" />
            Filters
          </button>
          <button
            onClick={handleExport}
            className="px-4 py-2 bg-gradient-to-r from-teal-500 to-emerald-600 text-white rounded-lg hover:from-teal-600 hover:to-emerald-700 transition-all flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Statistics Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-xl border border-white/10 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400 mb-1">Total Events</p>
                <p className="text-2xl font-bold text-white">{stats.total_logs.toLocaleString()}</p>
              </div>
              <Activity className="w-8 h-8 text-teal-400" />
            </div>
          </div>

          <div className="bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-xl border border-white/10 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400 mb-1">Success Rate</p>
                <p className="text-2xl font-bold text-green-400">
                  {stats.status_breakdown.success && stats.total_logs > 0 
                    ? ((stats.status_breakdown.success / stats.total_logs) * 100).toFixed(1) 
                    : 0}%
                </p>
              </div>
              <CheckCircle className="w-8 h-8 text-green-400" />
            </div>
          </div>

          <div className="bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-xl border border-white/10 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400 mb-1">Actions Today</p>
                <p className="text-2xl font-bold text-blue-400">
                  {Object.values(stats.actions_breakdown).reduce((sum, count) => sum + count, 0)}
                </p>
              </div>
              <Shield className="w-8 h-8 text-blue-400" />
            </div>
          </div>

          <div className="bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-xl border border-white/10 rounded-xl p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-400 mb-1">Active Users</p>
                <p className="text-2xl font-bold text-purple-400">{stats.top_users.length}</p>
              </div>
              <Eye className="w-8 h-8 text-purple-400" />
            </div>
          </div>
        </div>
      )}

      {/* Filter Panel */}
      {showFilters && (
        <div className="bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-xl border border-white/10 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-white mb-4">Filter Options</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-gray-400 mb-2">Start Date</label>
              <input
                type="datetime-local"
                value={filters.start_date}
                onChange={(e) => handleFilterChange('start_date', e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-400"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">End Date</label>
              <input
                type="datetime-local"
                value={filters.end_date}
                onChange={(e) => handleFilterChange('end_date', e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-400"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Action</label>
              <select
                value={filters.action}
                onChange={(e) => handleFilterChange('action', e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-400"
              >
                <option value="">All Actions</option>
                <option value="CREATE">CREATE</option>
                <option value="UPDATE">UPDATE</option>
                <option value="DELETE">DELETE</option>
                <option value="READ">READ</option>
                <option value="LOGIN">LOGIN</option>
                <option value="LOGOUT">LOGOUT</option>
                <option value="EXPORT">EXPORT</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Entity Type</label>
              <input
                type="text"
                value={filters.entity_type}
                onChange={(e) => handleFilterChange('entity_type', e.target.value)}
                placeholder="e.g. Invoice, Employee"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-400"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-2">Status</label>
              <select
                value={filters.status}
                onChange={(e) => handleFilterChange('status', e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-teal-400"
              >
                <option value="">All Statuses</option>
                <option value="success">Success</option>
                <option value="failure">Failure</option>
                <option value="error">Error</option>
              </select>
            </div>
          </div>
          <div className="mt-4 flex gap-3">
            <button
              onClick={handleApplyFilters}
              className="px-4 py-2 bg-gradient-to-r from-teal-500 to-emerald-600 text-white rounded-lg hover:from-teal-600 hover:to-emerald-700 transition-all"
            >
              Apply Filters
            </button>
            <button
              onClick={handleClearFilters}
              className="px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white hover:bg-white/10 transition-colors"
            >
              Clear Filters
            </button>
          </div>
        </div>
      )}

      {/* Search Bar */}
      <div className="relative">
        <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search by action, user, or entity type..."
          className="w-full bg-white/5 border border-white/10 rounded-lg pl-12 pr-4 py-3 text-white placeholder-gray-400 focus:outline-none focus:border-teal-400"
        />
      </div>

      {/* Audit Logs Table */}
      <div className="bg-gradient-to-br from-white/5 to-white/10 backdrop-blur-xl border border-white/10 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-white/5 border-b border-white/10">
              <tr>
                <th className="text-left p-4 text-sm font-semibold text-gray-300">Timestamp</th>
                <th className="text-left p-4 text-sm font-semibold text-gray-300">User</th>
                <th className="text-left p-4 text-sm font-semibold text-gray-300">Action</th>
                <th className="text-left p-4 text-sm font-semibold text-gray-300">Entity</th>
                <th className="text-left p-4 text-sm font-semibold text-gray-300">Status</th>
                <th className="text-left p-4 text-sm font-semibold text-gray-300">IP Address</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/10">
              {loading ? (
                <tr>
                  <td colSpan="6" className="text-center p-8 text-gray-400">
                    Loading audit logs...
                  </td>
                </tr>
              ) : filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan="6" className="text-center p-8 text-gray-400">
                    No audit logs found
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-white/5 transition-colors">
                    <td className="p-4 text-sm text-gray-300">
                      {new Date(log.timestamp).toLocaleString()}
                    </td>
                    <td className="p-4 text-sm text-white">
                      {log.user_email || <span className="text-gray-400">System</span>}
                    </td>
                    <td className="p-4">
                      <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-lg text-xs font-medium border ${getActionColor(log.action)}`}>
                        {getActionIcon(log.action)}
                        {log.action}
                      </span>
                    </td>
                    <td className="p-4 text-sm text-gray-300">
                      <div>
                        <span className="font-medium text-white">{log.entity_type || '-'}</span>
                        {log.entity_id && (
                          <span className="text-xs text-gray-400 block truncate max-w-[200px]">
                            ID: {log.entity_id}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="p-4">
                      {getStatusBadge(log.status)}
                    </td>
                    <td className="p-4 text-sm text-gray-400">
                      {log.ip_address || '-'}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
