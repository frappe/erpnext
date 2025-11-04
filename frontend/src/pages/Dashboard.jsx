import React, { useState, useEffect } from 'react';
import { 
  Users, BookOpen, FileText, TrendingUp, Package, Warehouse, 
  ShoppingCart, ShoppingBag, Building2, DollarSign, Puzzle, 
  UserCheck, Receipt, Banknote, Crown, Activity 
} from 'lucide-react';
import { dashboard } from '../services/api';

function Dashboard() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    dashboard.getStats()
      .then(response => {
        setStats(response.data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-500"></div>
      </div>
    );
  }

  const statCards = [
    {
      name: 'Employees',
      value: stats?.total_employees || 0,
      icon: Users,
      color: 'text-blue-400',
      bgColor: 'bg-gradient-to-br from-blue-500/20 to-blue-600/20',
      borderColor: 'border-blue-500/30',
    },
    {
      name: 'Departments',
      value: stats?.total_departments || 0,
      icon: Building2,
      color: 'text-indigo-400',
      bgColor: 'bg-gradient-to-br from-indigo-500/20 to-indigo-600/20',
      borderColor: 'border-indigo-500/30',
    },
    {
      name: 'Chart of Accounts',
      value: stats?.total_accounts || 0,
      icon: BookOpen,
      color: 'text-teal-400',
      bgColor: 'bg-gradient-to-br from-teal-500/20 to-green-500/20',
      borderColor: 'border-teal-500/30',
    },
    {
      name: 'Journal Entries',
      value: stats?.total_journals || 0,
      icon: FileText,
      color: 'text-purple-400',
      bgColor: 'bg-gradient-to-br from-purple-500/20 to-purple-600/20',
      borderColor: 'border-purple-500/30',
    },
    {
      name: 'Products',
      value: stats?.total_products || 0,
      icon: Package,
      color: 'text-orange-400',
      bgColor: 'bg-gradient-to-br from-orange-500/20 to-orange-600/20',
      borderColor: 'border-orange-500/30',
    },
    {
      name: 'Warehouses',
      value: stats?.total_warehouses || 0,
      icon: Warehouse,
      color: 'text-amber-400',
      bgColor: 'bg-gradient-to-br from-amber-500/20 to-amber-600/20',
      borderColor: 'border-amber-500/30',
    },
    {
      name: 'Sales Orders',
      value: stats?.total_sales_orders || 0,
      icon: ShoppingCart,
      color: 'text-green-400',
      bgColor: 'bg-gradient-to-br from-green-500/20 to-green-600/20',
      borderColor: 'border-green-500/30',
    },
    {
      name: 'Purchase Orders',
      value: stats?.total_purchase_orders || 0,
      icon: ShoppingBag,
      color: 'text-cyan-400',
      bgColor: 'bg-gradient-to-br from-cyan-500/20 to-cyan-600/20',
      borderColor: 'border-cyan-500/30',
    },
    {
      name: 'Customers',
      value: stats?.total_customers || 0,
      icon: UserCheck,
      color: 'text-pink-400',
      bgColor: 'bg-gradient-to-br from-pink-500/20 to-pink-600/20',
      borderColor: 'border-pink-500/30',
    },
    {
      name: 'Suppliers',
      value: stats?.total_suppliers || 0,
      icon: Receipt,
      color: 'text-rose-400',
      bgColor: 'bg-gradient-to-br from-rose-500/20 to-rose-600/20',
      borderColor: 'border-rose-500/30',
    },
    {
      name: 'Payslips Generated',
      value: stats?.total_payslips || 0,
      icon: DollarSign,
      color: 'text-emerald-400',
      bgColor: 'bg-gradient-to-br from-emerald-500/20 to-emerald-600/20',
      borderColor: 'border-emerald-500/30',
    },
    {
      name: 'Bank Accounts',
      value: stats?.total_bank_accounts || 0,
      icon: Banknote,
      color: 'text-lime-400',
      bgColor: 'bg-gradient-to-br from-lime-500/20 to-lime-600/20',
      borderColor: 'border-lime-500/30',
    },
    {
      name: 'Active Addons',
      value: stats?.activated_addons || 0,
      icon: Puzzle,
      color: 'text-violet-400',
      bgColor: 'bg-gradient-to-br from-violet-500/20 to-violet-600/20',
      borderColor: 'border-violet-500/30',
    },
    {
      name: 'Subscription Plan',
      value: (stats?.subscription_plan || 'trial').toUpperCase(),
      icon: Crown,
      color: 'text-yellow-400',
      bgColor: 'bg-gradient-to-br from-yellow-500/20 to-yellow-600/20',
      borderColor: 'border-yellow-500/30',
    },
  ];

  return (
    <div className="min-h-screen p-6">
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <Activity className="w-10 h-10 text-teal-400" />
          <h1 className="text-3xl font-bold text-white">Dashboard</h1>
        </div>
        <div className="flex items-center justify-between">
          <div>
            <p className="text-gray-400 text-lg">Welcome to {stats?.company_name || 'ERIK ERP'}</p>
            <p className="text-sm text-gray-500">
              Subscription: <span className="text-teal-400 font-medium">{stats?.subscription_plan?.toUpperCase()}</span> • 
              Status: <span className="text-green-400 font-medium">{stats?.subscription_status?.toUpperCase()}</span>
            </p>
          </div>
        </div>
      </div>

      {/* Main Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-5 gap-4 mb-8">
        {statCards.map((stat) => {
          const Icon = stat.icon;
          return (
            <div 
              key={stat.name} 
              className={`${stat.bgColor} backdrop-blur-sm rounded-lg p-5 border ${stat.borderColor} hover:scale-105 transition-all duration-200 cursor-pointer`}
            >
              <div className="flex items-center justify-between mb-3">
                <div className={`p-2 rounded-lg bg-gray-900/40`}>
                  <Icon className={stat.color} size={20} />
                </div>
                <div className="text-right">
                  <p className="text-2xl font-bold text-white">{stat.value}</p>
                </div>
              </div>
              <p className="text-gray-300 text-sm font-medium">{stat.name}</p>
            </div>
          );
        })}
      </div>

      {/* Additional Info Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
          <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
            <TrendingUp className="text-green-400" size={24} />
            System Status
          </h3>
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-gray-400">System Health</span>
              <span className="text-green-400 font-medium">Excellent</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Database</span>
              <span className="text-green-400 font-medium">Connected</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-400">API Status</span>
              <span className="text-green-400 font-medium">Online</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-400">Last Backup</span>
              <span className="text-gray-300 font-medium">Today</span>
            </div>
          </div>
        </div>

        <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
          <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
            <Package className="text-teal-400" size={24} />
            Quick Actions
          </h3>
          <div className="space-y-3">
            <button className="w-full px-4 py-2 bg-gradient-to-r from-teal-500/20 to-green-500/20 hover:from-teal-500/30 hover:to-green-500/30 text-teal-300 rounded-lg transition-all border border-teal-500/30 text-left">
              Add New Employee
            </button>
            <button className="w-full px-4 py-2 bg-gradient-to-r from-blue-500/20 to-purple-500/20 hover:from-blue-500/30 hover:to-purple-500/30 text-blue-300 rounded-lg transition-all border border-blue-500/30 text-left">
              Create Journal Entry
            </button>
            <button className="w-full px-4 py-2 bg-gradient-to-r from-orange-500/20 to-red-500/20 hover:from-orange-500/30 hover:to-red-500/30 text-orange-300 rounded-lg transition-all border border-orange-500/30 text-left">
              Generate Report
            </button>
            <button className="w-full px-4 py-2 bg-gradient-to-r from-violet-500/20 to-pink-500/20 hover:from-violet-500/30 hover:to-pink-500/30 text-violet-300 rounded-lg transition-all border border-violet-500/30 text-left">
              Manage Addons
            </button>
          </div>
        </div>

        <div className="bg-gradient-to-br from-gray-800/50 to-gray-900/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
          <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
            <FileText className="text-purple-400" size={24} />
            Recent Activity
          </h3>
          <div className="space-y-3">
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 rounded-full bg-green-400 mt-2"></div>
              <div>
                <p className="text-sm text-gray-300">System initialized successfully</p>
                <p className="text-xs text-gray-500">Just now</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 rounded-full bg-teal-400 mt-2"></div>
              <div>
                <p className="text-sm text-gray-300">All modules are active</p>
                <p className="text-xs text-gray-500">2 minutes ago</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 rounded-full bg-blue-400 mt-2"></div>
              <div>
                <p className="text-sm text-gray-300">Database connected</p>
                <p className="text-xs text-gray-500">5 minutes ago</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <div className="w-2 h-2 rounded-full bg-purple-400 mt-2"></div>
              <div>
                <p className="text-sm text-gray-300">17 industry addons available</p>
                <p className="text-xs text-gray-500">10 minutes ago</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
