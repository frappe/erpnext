import React, { useState, useEffect } from 'react';
import { Users, BookOpen, FileText, TrendingUp } from 'lucide-react';
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
    return <div className="text-erik-primary">Loading...</div>;
  }

  const statCards = [
    {
      name: 'Total Employees',
      value: stats?.total_employees || 0,
      icon: Users,
      color: 'text-blue-400',
      bgColor: 'bg-blue-500/20',
    },
    {
      name: 'Chart of Accounts',
      value: stats?.total_accounts || 0,
      icon: BookOpen,
      color: 'text-erik-primary',
      bgColor: 'bg-erik-primary/20',
    },
    {
      name: 'Journal Entries',
      value: stats?.total_journals || 0,
      icon: FileText,
      color: 'text-purple-400',
      bgColor: 'bg-purple-500/20',
    },
    {
      name: 'Active Status',
      value: 'Running',
      icon: TrendingUp,
      color: 'text-green-400',
      bgColor: 'bg-green-500/20',
    },
  ];

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Dashboard</h1>
        <p className="text-gray-400">Welcome to {stats?.company_name || 'ERIK ERP'}</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {statCards.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.name} className="card">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-400 text-sm mb-1">{stat.name}</p>
                  <p className="text-2xl font-bold text-white">{stat.value}</p>
                </div>
                <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                  <Icon className={stat.color} size={24} />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="card">
          <h3 className="text-xl font-semibold text-white mb-4">Quick Actions</h3>
          <div className="space-y-3">
            <button className="btn-secondary w-full text-left">
              Add New Employee
            </button>
            <button className="btn-secondary w-full text-left">
              Create Journal Entry
            </button>
            <button className="btn-secondary w-full text-left">
              Generate Report
            </button>
          </div>
        </div>

        <div className="card">
          <h3 className="text-xl font-semibold text-white mb-4">Recent Activity</h3>
          <div className="space-y-3 text-gray-400">
            <p className="text-sm">System initialized successfully</p>
            <p className="text-sm">Ready to start managing your enterprise</p>
            <p className="text-sm">All modules are active</p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
