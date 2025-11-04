import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Landing from './pages/Landing';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Employees from './pages/Employees';
import Accounts from './pages/Accounts';
import Journals from './pages/Journals';
import Reports from './pages/Reports';
import Payroll from './pages/Payroll';
import Compliance from './pages/Compliance';
import Leave from './pages/Leave';
import Products from './pages/Products';
import Customers from './pages/Customers';
import Suppliers from './pages/Suppliers';
import SalesOrders from './pages/SalesOrders';
import PurchaseOrders from './pages/PurchaseOrders';
import AdminDashboard from './pages/AdminDashboard';
import MobileMoney from './pages/MobileMoney';
import Branches from './pages/Branches';
import POS from './pages/POS';
import SecuritySettings from './pages/SecuritySettings';
import AIAssistant from './pages/AIAssistant';
import StatutoryObligations from './pages/StatutoryObligations';
import Departments from './pages/Departments';
import ConsolidatedReports from './pages/ConsolidatedReports';
import Settings from './pages/Settings';
import AuditTrail from './pages/AuditTrail';
import BankConnections from './pages/Banking/BankConnections';
import TransactionFeed from './pages/Banking/TransactionFeed';
import ReconciliationDashboard from './pages/Banking/ReconciliationDashboard';
import SuperAdmin from './pages/SuperAdmin';
import Layout from './components/Layout';
import { auth } from './services/api';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      auth.getMe()
        .then(response => {
          setUser(response.data);
          setLoading(false);
        })
        .catch(() => {
          localStorage.removeItem('token');
          setLoading(false);
        });
    } else {
      setLoading(false);
    }
  }, []);

  const handleLogin = (token) => {
    localStorage.setItem('token', token);
    auth.getMe().then(response => {
      setUser(response.data);
    });
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null);
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center gradient-bg">
        <div className="text-center">
          <div className="text-4xl font-bold gradient-text mb-4">ERIK</div>
          <div className="text-erik-primary">Loading...</div>
        </div>
      </div>
    );
  }

  return (
    <Router>
      <Routes>
        <Route path="/" element={
          user ? <Navigate to="/dashboard" /> : <Landing />
        } />
        <Route path="/login" element={
          user ? <Navigate to="/dashboard" /> : <Login onLogin={handleLogin} />
        } />
        <Route path="/register" element={
          user ? <Navigate to="/dashboard" /> : <Register onLogin={handleLogin} />
        } />
        <Route path="/admin" element={
          user ? <AdminDashboard /> : <Navigate to="/login" />
        } />
        <Route path="/super-admin" element={
          user ? <SuperAdmin /> : <Navigate to="/login" />
        } />
        <Route path="/" element={
          user ? <Layout user={user} onLogout={handleLogout} /> : <Navigate to="/" />
        }>
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="reports" element={<Reports />} />
          <Route path="employees" element={<Employees />} />
          <Route path="payroll" element={<Payroll />} />
          <Route path="compliance" element={<Compliance />} />
          <Route path="leave" element={<Leave />} />
          <Route path="accounts" element={<Accounts />} />
          <Route path="journals" element={<Journals />} />
          <Route path="products" element={<Products />} />
          <Route path="customers" element={<Customers />} />
          <Route path="sales-orders" element={<SalesOrders />} />
          <Route path="suppliers" element={<Suppliers />} />
          <Route path="purchase-orders" element={<PurchaseOrders />} />
          <Route path="mobile-money" element={<MobileMoney />} />
          <Route path="branches" element={<Branches />} />
          <Route path="pos" element={<POS />} />
          <Route path="security" element={<SecuritySettings />} />
          <Route path="ai-assistant" element={<AIAssistant />} />
          <Route path="statutory-obligations" element={<StatutoryObligations />} />
          <Route path="departments" element={<Departments />} />
          <Route path="consolidated-reports" element={<ConsolidatedReports />} />
          <Route path="settings" element={<Settings />} />
          <Route path="audit-trail" element={<AuditTrail />} />
          <Route path="bank-connections" element={<BankConnections />} />
          <Route path="transaction-feed" element={<TransactionFeed />} />
          <Route path="reconciliation" element={<ReconciliationDashboard />} />
        </Route>
      </Routes>
    </Router>
  );
}

export default App;
