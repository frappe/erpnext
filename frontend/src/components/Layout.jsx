import React, { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Users, 
  BookOpen, 
  FileText, 
  Menu, 
  X, 
  LogOut 
} from 'lucide-react';

function Layout({ user, onLogout }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();

  const navigation = [
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
    { name: 'Employees', href: '/employees', icon: Users },
    { name: 'Accounts', href: '/accounts', icon: BookOpen },
    { name: 'Journals', href: '/journals', icon: FileText },
  ];

  return (
    <div className="min-h-screen gradient-bg">
      <nav className="bg-erik-light border-b border-erik-primary/20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <button
                onClick={() => setSidebarOpen(!sidebarOpen)}
                className="p-2 rounded-md text-erik-primary hover:bg-erik-dark/50"
              >
                {sidebarOpen ? <X size={24} /> : <Menu size={24} />}
              </button>
              <span className="ml-4 text-2xl font-bold gradient-text">ERIK</span>
              <span className="ml-2 text-sm text-gray-400">ERP</span>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-gray-300">{user.full_name}</span>
              <button
                onClick={onLogout}
                className="p-2 rounded-md text-erik-primary hover:bg-erik-dark/50"
              >
                <LogOut size={20} />
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div className="flex">
        {sidebarOpen && (
          <aside className="w-64 min-h-screen bg-erik-light border-r border-erik-primary/20">
            <nav className="mt-8 px-4 space-y-2">
              {navigation.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.href;
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={`flex items-center px-4 py-3 rounded-lg transition-all ${
                      isActive
                        ? 'bg-erik-primary/20 text-erik-primary border border-erik-primary/30'
                        : 'text-gray-300 hover:bg-erik-dark/50 hover:text-erik-primary'
                    }`}
                  >
                    <Icon size={20} className="mr-3" />
                    {item.name}
                  </Link>
                );
              })}
            </nav>
          </aside>
        )}

        <main className="flex-1 p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export default Layout;
