import React, { useState } from 'react';
import { Outlet, Link, useLocation } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Users, 
  BookOpen, 
  FileText, 
  Menu, 
  X, 
  LogOut,
  Package,
  ShoppingCart,
  TruckIcon,
  DollarSign,
  Calendar,
  BarChart3,
  Building,
  Smartphone
} from 'lucide-react';

function Layout({ user, onLogout }) {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const location = useLocation();

  const navigationSections = [
    {
      title: 'Main',
      items: [
        { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
        { name: 'Reports', href: '/reports', icon: BarChart3 },
      ]
    },
    {
      title: 'HR & Payroll',
      items: [
        { name: 'Employees', href: '/employees', icon: Users },
        { name: 'Payroll', href: '/payroll', icon: DollarSign },
        { name: 'Leave', href: '/leave', icon: Calendar },
      ]
    },
    {
      title: 'Finance',
      items: [
        { name: 'Accounts', href: '/accounts', icon: BookOpen },
        { name: 'Journals', href: '/journals', icon: FileText },
      ]
    },
    {
      title: 'Inventory & Sales',
      items: [
        { name: 'Products', href: '/products', icon: Package },
        { name: 'Customers', href: '/customers', icon: Users },
        { name: 'Sales Orders', href: '/sales-orders', icon: ShoppingCart },
      ]
    },
    {
      title: 'Procurement',
      items: [
        { name: 'Suppliers', href: '/suppliers', icon: TruckIcon },
        { name: 'Purchase Orders', href: '/purchase-orders', icon: ShoppingCart },
      ]
    },
    {
      title: 'Operations',
      items: [
        { name: 'Point of Sale', href: '/pos', icon: ShoppingCart },
        { name: 'Branches', href: '/branches', icon: Building },
        { name: 'Mobile Money', href: '/mobile-money', icon: Smartphone },
      ]
    }
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
              <img src="/assets/erik-logo.png" alt="ERIK ERP" className="ml-4 h-8 w-auto" />
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
          <aside className="w-64 min-h-screen bg-erik-light border-r border-erik-primary/20 overflow-y-auto">
            <nav className="mt-8 px-4 space-y-6 pb-8">
              {navigationSections.map((section) => (
                <div key={section.title}>
                  <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 px-4">
                    {section.title}
                  </h3>
                  <div className="space-y-1">
                    {section.items.map((item) => {
                      const Icon = item.icon;
                      const isActive = location.pathname === item.href;
                      return (
                        <Link
                          key={item.name}
                          to={item.href}
                          className={`flex items-center px-4 py-2 rounded-lg transition-all ${
                            isActive
                              ? 'bg-erik-primary/20 text-erik-primary border border-erik-primary/30'
                              : 'text-gray-300 hover:bg-erik-dark/50 hover:text-erik-primary'
                          }`}
                        >
                          <Icon size={18} className="mr-3" />
                          <span className="text-sm">{item.name}</span>
                        </Link>
                      );
                    })}
                  </div>
                </div>
              ))}
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
