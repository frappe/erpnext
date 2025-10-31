import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { 
  Building2, Users, TrendingUp, DollarSign,
  UserCheck, Clock, CheckCircle, XCircle,
  Activity, BarChart3, Shield
} from 'lucide-react'
import api from '../services/api'

export default function AdminDashboard() {
  const navigate = useNavigate()
  const [stats, setStats] = useState(null)
  const [companies, setCompanies] = useState([])
  const [analytics, setAnalytics] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [statsRes, companiesRes, analyticsRes] = await Promise.all([
        api.get('/api/admin/stats'),
        api.get('/api/admin/companies'),
        api.get('/api/admin/analytics')
      ])
      
      setStats(statsRes.data)
      setCompanies(companiesRes.data)
      setAnalytics(analyticsRes.data.analytics)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching admin data:', error)
      if (error.response?.status === 403) {
        alert('Access denied. Super admin privileges required.')
        navigate('/dashboard')
      }
    }
  }

  const toggleCompanyStatus = async (companyId) => {
    try {
      await api.put(`/api/admin/companies/${companyId}/toggle-status`)
      fetchData()
    } catch (error) {
      console.error('Error toggling company status:', error)
      alert('Failed to update company status')
    }
  }

  const updateSubscription = async (companyId, plan, status) => {
    try {
      await api.put(`/api/admin/companies/${companyId}/subscription`, null, {
        params: { plan, status }
      })
      fetchData()
    } catch (error) {
      console.error('Error updating subscription:', error)
      alert('Failed to update subscription')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gradient-to-br from-gray-900 to-gray-800">
        <div className="text-erik-primary text-2xl">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 to-gray-800 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <Shield className="w-10 h-10 text-erik-primary" />
              <h1 className="text-4xl font-bold text-white">Super Admin Dashboard</h1>
            </div>
            <p className="text-gray-400">Platform Overview & Tenant Management</p>
          </div>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-6 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
          >
            Back to Main
          </button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <Building2 className="w-8 h-8 opacity-80" />
              <span className="text-3xl font-bold">{stats?.total_companies || 0}</span>
            </div>
            <p className="text-sm opacity-90">Total Companies</p>
          </div>

          <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <CheckCircle className="w-8 h-8 opacity-80" />
              <span className="text-3xl font-bold">{stats?.active_companies || 0}</span>
            </div>
            <p className="text-sm opacity-90">Active Companies</p>
          </div>

          <div className="bg-gradient-to-br from-yellow-500 to-yellow-600 rounded-xl p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <Clock className="w-8 h-8 opacity-80" />
              <span className="text-3xl font-bold">{stats?.trial_companies || 0}</span>
            </div>
            <p className="text-sm opacity-90">Trial Companies</p>
          </div>

          <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <DollarSign className="w-8 h-8 opacity-80" />
              <span className="text-3xl font-bold">{stats?.paid_companies || 0}</span>
            </div>
            <p className="text-sm opacity-90">Paid Companies</p>
          </div>

          <div className="bg-gradient-to-br from-teal-500 to-teal-600 rounded-xl p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <Users className="w-8 h-8 opacity-80" />
              <span className="text-3xl font-bold">{stats?.total_users || 0}</span>
            </div>
            <p className="text-sm opacity-90">Total Users</p>
          </div>

          <div className="bg-gradient-to-br from-pink-500 to-pink-600 rounded-xl p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <UserCheck className="w-8 h-8 opacity-80" />
              <span className="text-3xl font-bold">{stats?.total_employees || 0}</span>
            </div>
            <p className="text-sm opacity-90">Total Employees</p>
          </div>

          <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <Activity className="w-8 h-8 opacity-80" />
              <span className="text-3xl font-bold">{stats?.total_transactions || 0}</span>
            </div>
            <p className="text-sm opacity-90">Total Transactions</p>
          </div>

          <div className="bg-gradient-to-br from-indigo-500 to-indigo-600 rounded-xl p-6 text-white">
            <div className="flex items-center justify-between mb-4">
              <TrendingUp className="w-8 h-8 opacity-80" />
              <span className="text-3xl font-bold">ZMW 0</span>
            </div>
            <p className="text-sm opacity-90">Total Revenue</p>
          </div>
        </div>

        {/* Companies Table */}
        <div className="bg-erik-light/30 backdrop-blur-lg rounded-xl p-6 border border-erik-primary/30">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-2xl font-bold text-white flex items-center gap-2">
              <Building2 className="w-6 h-6 text-erik-primary" />
              All Companies
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-white">
              <thead className="bg-erik-dark/50">
                <tr>
                  <th className="px-4 py-3 text-erik-primary">Company Name</th>
                  <th className="px-4 py-3 text-erik-primary">Email</th>
                  <th className="px-4 py-3 text-erik-primary">Plan</th>
                  <th className="px-4 py-3 text-erik-primary">Status</th>
                  <th className="px-4 py-3 text-erik-primary">Trial Ends</th>
                  <th className="px-4 py-3 text-erik-primary">Created</th>
                  <th className="px-4 py-3 text-erik-primary">Actions</th>
                </tr>
              </thead>
              <tbody>
                {companies.map((company) => (
                  <tr key={company.id} className="border-b border-gray-700 hover:bg-erik-dark/30">
                    <td className="px-4 py-3 font-medium">{company.name}</td>
                    <td className="px-4 py-3 text-gray-300">{company.email || 'N/A'}</td>
                    <td className="px-4 py-3">
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                        company.subscription_plan === 'trial' ? 'bg-yellow-500/20 text-yellow-400' :
                        company.subscription_plan === 'premium' ? 'bg-purple-500/20 text-purple-400' :
                        'bg-green-500/20 text-green-400'
                      }`}>
                        {company.subscription_plan.toUpperCase()}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      {company.is_active ? (
                        <span className="flex items-center gap-1 text-green-400">
                          <CheckCircle className="w-4 h-4" /> Active
                        </span>
                      ) : (
                        <span className="flex items-center gap-1 text-red-400">
                          <XCircle className="w-4 h-4" /> Inactive
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-300">
                      {company.trial_ends_at ? new Date(company.trial_ends_at).toLocaleDateString() : 'N/A'}
                    </td>
                    <td className="px-4 py-3 text-gray-300">
                      {new Date(company.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex gap-2">
                        <button
                          onClick={() => toggleCompanyStatus(company.id)}
                          className={`px-3 py-1 rounded text-xs font-medium ${
                            company.is_active 
                              ? 'bg-red-500 hover:bg-red-600' 
                              : 'bg-green-500 hover:bg-green-600'
                          } text-white`}
                        >
                          {company.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                        <select
                          value={company.subscription_plan}
                          onChange={(e) => updateSubscription(company.id, e.target.value, company.subscription_status)}
                          className="px-2 py-1 bg-erik-dark border border-erik-primary/30 rounded text-xs text-white"
                        >
                          <option value="trial">Trial</option>
                          <option value="basic">Basic</option>
                          <option value="premium">Premium</option>
                          <option value="enterprise">Enterprise</option>
                        </select>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Analytics Summary */}
        <div className="mt-8 bg-erik-light/30 backdrop-blur-lg rounded-xl p-6 border border-erik-primary/30">
          <h2 className="text-2xl font-bold text-white mb-6 flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-erik-primary" />
            Company Analytics
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {analytics.slice(0, 6).map((item) => (
              <div key={item.company_id} className="bg-erik-dark/50 rounded-lg p-4 border border-gray-700">
                <h3 className="text-white font-bold mb-2">{item.company_name}</h3>
                <div className="space-y-1 text-sm text-gray-300">
                  <p>Users: <span className="text-erik-primary font-medium">{item.user_count}</span></p>
                  <p>Employees: <span className="text-erik-primary font-medium">{item.employee_count}</span></p>
                  <p>Transactions: <span className="text-erik-primary font-medium">{item.transaction_count}</span></p>
                  <p className="text-xs text-gray-400 mt-2">
                    Created: {new Date(item.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
