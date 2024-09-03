import React from 'react';
import { BrowserRouter as Router, Switch, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { LoginForm } from './components/LoginForm';
import { Dashboard } from './components/Dashboard';
import { ItemForm } from './components/ItemForm';
import { LeadForm } from './components/LeadForm';
import { LeadList } from './components/LeadList';
import { WorkOrderForm } from './components/WorkOrderForm';
import { WorkOrderList } from './components/WorkOrderList';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout';

function App() {
  return (
    <AuthProvider>
      <Router>
        <Switch>
          <Route path="/login" component={LoginForm} />
          <Layout>
            <ProtectedRoute exact path="/" component={Dashboard} />
            <ProtectedRoute path="/items/new" component={ItemForm} />
            <ProtectedRoute exact path="/crm/leads" component={LeadList} />
            <ProtectedRoute path="/crm/leads/new" component={LeadForm} />
            <ProtectedRoute exact path="/manufacturing/work-orders" component={WorkOrderList} />
            <ProtectedRoute path="/manufacturing/work-orders/new" component={WorkOrderForm} />
          </Layout>
        </Switch>
      </Router>
    </AuthProvider>
  );
}

export default App;