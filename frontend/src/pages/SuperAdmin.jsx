import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  CreditCard,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Clock,
  DollarSign,
  Activity,
  Settings,
  Search,
  Filter,
  MoreVertical,
  XCircle,
  Play,
  Shield
} from 'lucide-react';
import api from '../services/api';
import { auth } from '../services/api';

export default function SuperAdmin() {
  const navigate = useNavigate();
  const [analytics, setAnalytics] = useState(null);
  const [tenants, setTenants] = useState([]);
  const [plans, setPlans] = useState([]);
  const [tickets, setTickets] = useState([]);
  const [activeTab, setActiveTab] = useState('overview');
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterStatus, setFilterStatus] = useState('all');
  const [unauthorized, setUnauthorized] = useState(false);

  useEffect(() => {
    checkSuperAdminAccess();
  }, []);

  const checkSuperAdminAccess = async () => {
    try {
      const response = await auth.getMe();
      const user = response.data;
      
      if (!user.is_super_admin) {
        setUnauthorized(true);
        setLoading(false);
        return;
      }
      
      fetchData();
    } catch (error) {
      console.error('Failed to verify super admin access:', error);
      navigate('/dashboard');
    }
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const [analyticsRes, tenantsRes, plansRes, ticketsRes] = await Promise.all([
        api.get('/api/super-admin/analytics/dashboard'),
        api.get('/api/super-admin/tenants'),
        api.get('/api/super-admin/subscription-plans'),
        api.get('/api/super-admin/support/tickets?limit=10')
      ]);

      setAnalytics(analyticsRes.data);
      setTenants(tenantsRes.data.tenants || []);
      setPlans(plansRes.data.plans || []);
      setTickets(ticketsRes.data.tickets || []);
    } catch (error) {
      console.error('Failed to fetch super admin data:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleSuspendTenant = async (tenantId) => {
    if (!confirm('Are you sure you want to suspend this tenant?')) return;

    try {
      await api.post(`/api/super-admin/tenants/${tenantId}/suspend`);
      fetchData();
    } catch (error) {
      console.error('Failed to suspend tenant:', error);
      alert('Failed to suspend tenant');
    }
  };

  const handleActivateTenant = async (tenantId) => {
    try {
      await api.post(`/api/super-admin/tenants/${tenantId}/activate`);
      fetchData();
    } catch (error) {
      console.error('Failed to activate tenant:', error);
      alert('Failed to activate tenant');
    }
  };

  const filteredTenants = tenants.filter(tenant => {
    const matchesSearch = tenant.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
                         tenant.email.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesStatus = filterStatus === 'all' || tenant.subscription_status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  if (unauthorized) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="text-center max-w-md p-8 bg-gradient-to-br from-red-900/40 to-red-800/40 backdrop-blur-xl rounded-xl border border-red-500/20 shadow-lg">
          <Shield className="w-16 h-16 text-red-400 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-white mb-2">Access Denied</h1>
          <p className="text-gray-400 mb-6">
            You do not have super admin privileges. This area is restricted to platform administrators only.
          </p>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-6 py-3 bg-red-600 hover:bg-red-700 text-white rounded-lg transition-colors"
          >
            Return to Dashboard
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-teal-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-gray-400">Loading Super Admin Dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-900/40 to-pink-900/40 backdrop-blur-xl border-b border-purple-500/20 shadow-lg">
        <div className="max-w-7xl mx-auto px-6 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
                Super Admin Dashboard
              </h1>
              <p className="text-gray-400 mt-1">Platform-wide management & analytics</p>
            </div>
            <div className="flex items-center space-x-3">
              <button className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg transition-colors">
                <Settings className="w-4 h-4 inline mr-2" />
                Platform Settings
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex space-x-1 mt-6">
            {[
              { id: 'overview', label: 'Overview' },
              { id: 'tenants', label: 'Tenants' },
              { id: 'plans', label: 'Plans' },
              { id: 'support', label: 'Support' }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-t-lg font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-purple-600 text-white'
                    : 'bg-gray-800/50 text-gray-400 hover:bg-gray-700/50'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Overview Tab */}
        {activeTab === 'overview' && analytics && (
          <div className="space-y-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {/* Total Tenants */}
              <div className="bg-gradient-to-br from-blue-900/40 to-blue-800/40 backdrop-blur-xl rounded-xl border border-blue-500/20 p-6 shadow-lg">
                <div className="flex items-center justify-between mb-4">
                  <Users className="w-8 h-8 text-blue-400" />
                  <span className="text-xs text-blue-400 bg-blue-500/20 px-2 py-1 rounded-full">
                    +{analytics.tenant_stats.new_this_month} this month
                  </span>
                </div>
                <p className="text-gray-400 text-sm">Total Tenants</p>
                <p className="text-3xl font-bold text-white mt-1">
                  {analytics.tenant_stats.total}
                </p>
              </div>

              {/* Active Tenants */}
              <div className="bg-gradient-to-br from-green-900/40 to-green-800/40 backdrop-blur-xl rounded-xl border border-green-500/20 p-6 shadow-lg">
                <div className="flex items-center justify-between mb-4">
                  <CheckCircle className="w-8 h-8 text-green-400" />
                </div>
                <p className="text-gray-400 text-sm">Active Tenants</p>
                <p className="text-3xl font-bold text-white mt-1">
                  {analytics.tenant_stats.active}
                </p>
              </div>

              {/* Trial Tenants */}
              <div className="bg-gradient-to-br from-yellow-900/40 to-yellow-800/40 backdrop-blur-xl rounded-xl border border-yellow-500/20 p-6 shadow-lg">
                <div className="flex items-center justify-between mb-4">
                  <Clock className="w-8 h-8 text-yellow-400" />
                </div>
                <p className="text-gray-400 text-sm">Trial Tenants</p>
                <p className="text-3xl font-bold text-white mt-1">
                  {analytics.tenant_stats.trial}
                </p>
              </div>

              {/* Open Tickets */}
              <div className="bg-gradient-to-br from-red-900/40 to-red-800/40 backdrop-blur-xl rounded-xl border border-red-500/20 p-6 shadow-lg">
                <div className="flex items-center justify-between mb-4">
                  <AlertCircle className="w-8 h-8 text-red-400" />
                </div>
                <p className="text-gray-400 text-sm">Open Tickets</p>
                <p className="text-3xl font-bold text-white mt-1">
                  {analytics.support.open_tickets}
                </p>
              </div>
            </div>

            {/* Subscription Breakdown */}
            <div className="bg-gradient-to-br from-gray-800/40 to-gray-900/40 backdrop-blur-xl rounded-xl border border-gray-700/50 p-6 shadow-lg">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
                <CreditCard className="w-5 h-5 mr-2 text-purple-400" />
                Subscription Breakdown
              </h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {analytics.subscription_breakdown.map((item) => (
                  <div key={item.plan} className="text-center p-4 bg-gray-800/50 rounded-lg">
                    <p className="text-2xl font-bold text-white">{item.count}</p>
                    <p className="text-sm text-gray-400 capitalize mt-1">{item.plan}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Tenants Tab */}
        {activeTab === 'tenants' && (
          <div className="space-y-6">
            {/* Search & Filter */}
            <div className="bg-gradient-to-br from-gray-800/40 to-gray-900/40 backdrop-blur-xl rounded-xl border border-gray-700/50 p-4 shadow-lg">
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1 relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                  <input
                    type="text"
                    placeholder="Search by name or email..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                  />
                </div>
                <select
                  value={filterStatus}
                  onChange={(e) => setFilterStatus(e.target.value)}
                  className="px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:border-purple-500 focus:outline-none"
                >
                  <option value="all">All Status</option>
                  <option value="active">Active</option>
                  <option value="trial">Trial</option>
                  <option value="suspended">Suspended</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>
            </div>

            {/* Tenants List */}
            <div className="bg-gradient-to-br from-gray-800/40 to-gray-900/40 backdrop-blur-xl rounded-xl border border-gray-700/50 shadow-lg overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-800/50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Company</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Plan</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Status</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Users</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Created</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-700/50">
                    {filteredTenants.map((tenant) => (
                      <tr key={tenant.id} className="hover:bg-gray-800/30">
                        <td className="px-6 py-4">
                          <div>
                            <p className="text-white font-medium">{tenant.name}</p>
                            <p className="text-sm text-gray-400">{tenant.email}</p>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className="px-2 py-1 bg-purple-500/20 text-purple-400 text-xs rounded-full capitalize">
                            {tenant.subscription_plan}
                          </span>
                        </td>
                        <td className="px-6 py-4">
                          <span className={`px-2 py-1 text-xs rounded-full capitalize ${
                            tenant.subscription_status === 'active'
                              ? 'bg-green-500/20 text-green-400'
                              : tenant.subscription_status === 'trial'
                              ? 'bg-yellow-500/20 text-yellow-400'
                              : 'bg-red-500/20 text-red-400'
                          }`}>
                            {tenant.subscription_status}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-white">{tenant.user_count}</td>
                        <td className="px-6 py-4 text-gray-400 text-sm">
                          {new Date(tenant.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex space-x-2">
                            {tenant.is_active ? (
                              <button
                                onClick={() => handleSuspendTenant(tenant.id)}
                                className="p-2 text-red-400 hover:bg-red-500/20 rounded-lg transition-colors"
                                title="Suspend"
                              >
                                <XCircle className="w-4 h-4" />
                              </button>
                            ) : (
                              <button
                                onClick={() => handleActivateTenant(tenant.id)}
                                className="p-2 text-green-400 hover:bg-green-500/20 rounded-lg transition-colors"
                                title="Activate"
                              >
                                <Play className="w-4 h-4" />
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Plans Tab */}
        {activeTab === 'plans' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {plans.map((plan) => (
              <div
                key={plan.id}
                className="bg-gradient-to-br from-gray-800/40 to-gray-900/40 backdrop-blur-xl rounded-xl border border-gray-700/50 p-6 shadow-lg"
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xl font-bold text-white capitalize">{plan.plan_name}</h3>
                  <span className="px-2 py-1 bg-purple-500/20 text-purple-400 text-xs rounded-full">
                    {plan.tenant_count} tenants
                  </span>
                </div>
                <p className="text-gray-400 text-sm mb-4">{plan.description}</p>
                <div className="space-y-2 mb-4">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Monthly</span>
                    <span className="text-white font-semibold">
                      {plan.currency} {plan.price_monthly.toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">Annual</span>
                    <span className="text-white font-semibold">
                      {plan.currency} {plan.price_annual.toFixed(2)}
                    </span>
                  </div>
                </div>
                <div className="border-t border-gray-700 pt-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">Max Users</span>
                    <span className="text-white">{plan.max_users}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Max Employees</span>
                    <span className="text-white">{plan.max_employees}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Storage</span>
                    <span className="text-white">{plan.max_storage_gb} GB</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Branches</span>
                    <span className="text-white">{plan.max_branches}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Support Tab */}
        {activeTab === 'support' && (
          <div className="bg-gradient-to-br from-gray-800/40 to-gray-900/40 backdrop-blur-xl rounded-xl border border-gray-700/50 shadow-lg overflow-hidden">
            <div className="p-6">
              <h3 className="text-lg font-semibold text-white mb-4">Recent Support Tickets</h3>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-800/50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Ticket #</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Subject</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Priority</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase">Created</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-700/50">
                  {tickets.map((ticket) => (
                    <tr key={ticket.id} className="hover:bg-gray-800/30">
                      <td className="px-6 py-4 text-white font-mono text-sm">{ticket.ticket_number}</td>
                      <td className="px-6 py-4 text-white">{ticket.subject}</td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 text-xs rounded-full capitalize ${
                          ticket.priority === 'critical'
                            ? 'bg-red-500/20 text-red-400'
                            : ticket.priority === 'high'
                            ? 'bg-orange-500/20 text-orange-400'
                            : ticket.priority === 'medium'
                            ? 'bg-yellow-500/20 text-yellow-400'
                            : 'bg-blue-500/20 text-blue-400'
                        }`}>
                          {ticket.priority}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 text-xs rounded-full capitalize ${
                          ticket.status === 'resolved'
                            ? 'bg-green-500/20 text-green-400'
                            : ticket.status === 'in_progress'
                            ? 'bg-blue-500/20 text-blue-400'
                            : 'bg-gray-500/20 text-gray-400'
                        }`}>
                          {ticket.status.replace('_', ' ')}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-gray-400 text-sm">
                        {new Date(ticket.created_at).toLocaleDateString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
