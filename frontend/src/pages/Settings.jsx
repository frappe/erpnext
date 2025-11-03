import React, { useState, useEffect } from 'react';
import { Settings as SettingsIcon, Save, Plus, Trash2, Edit2, Check, X } from 'lucide-react';
import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000/api';

function Settings() {
  const [activeTab, setActiveTab] = useState('system');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const tabs = [
    { id: 'system', name: 'System Settings', icon: SettingsIcon },
    { id: 'leave', name: 'Leave Types', icon: SettingsIcon },
    { id: 'tax', name: 'Tax Settings', icon: SettingsIcon },
    { id: 'email', name: 'Email Templates', icon: SettingsIcon },
    { id: 'salary', name: 'Salary Components', icon: SettingsIcon },
    { id: 'workflows', name: 'Approval Workflows', icon: SettingsIcon },
  ];

  const showMessage = (msg, type = 'success') => {
    setMessage({ text: msg, type });
    setTimeout(() => setMessage(null), 3000);
  };

  return (
    <div>
      <div className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Settings</h1>
          <p className="text-gray-400">Configure your ERIK ERP system</p>
        </div>
        <button
          onClick={async () => {
            if (confirm('Seed default Zambian tax settings and salary components?')) {
              try {
                const token = localStorage.getItem('token');
                await axios.post(`${API_URL}/settings/seed-defaults`, {}, {
                  headers: { Authorization: `Bearer ${token}` }
                });
                showMessage('Default settings seeded successfully!');
              } catch (error) {
                showMessage(error.response?.data?.detail || 'Error seeding defaults', 'error');
              }
            }
          }}
          className="btn-primary"
        >
          <Plus size={20} className="mr-2" />
          Seed Defaults
        </button>
      </div>

      {message && (
        <div className={`mb-4 p-4 rounded-lg ${message.type === 'success' ? 'bg-erik-primary/20 text-erik-primary' : 'bg-red-500/20 text-red-400'}`}>
          {message.text}
        </div>
      )}

      <div className="card">
        <div className="border-b border-gray-700 mb-6">
          <div className="flex space-x-1">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-6 py-3 font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'text-erik-primary border-b-2 border-erik-primary'
                    : 'text-gray-400 hover:text-white'
                }`}
              >
                {tab.name}
              </button>
            ))}
          </div>
        </div>

        <div className="min-h-[500px]">
          {activeTab === 'system' && <SystemSettings showMessage={showMessage} />}
          {activeTab === 'leave' && <LeaveTypeSettings showMessage={showMessage} />}
          {activeTab === 'tax' && <TaxSettings showMessage={showMessage} />}
          {activeTab === 'email' && <EmailTemplates showMessage={showMessage} />}
          {activeTab === 'salary' && <SalaryComponents showMessage={showMessage} />}
          {activeTab === 'workflows' && <ApprovalWorkflows showMessage={showMessage} />}
        </div>
      </div>
    </div>
  );
}

// System Settings Component
function SystemSettings({ showMessage }) {
  const [settings, setSettings] = useState([]);
  const [editMode, setEditMode] = useState(null);
  const [formData, setFormData] = useState({});

  useEffect(() => {
    fetchSettings();
  }, []);

  const fetchSettings = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/settings/system`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSettings(response.data);
    } catch (error) {
      console.error('Error fetching settings:', error);
    }
  };

  const handleSave = async (setting) => {
    try {
      const token = localStorage.getItem('token');
      if (setting.id) {
        await axios.put(`${API_URL}/settings/system/${setting.id}`, formData, {
          headers: { Authorization: `Bearer ${token}` }
        });
      } else {
        await axios.post(`${API_URL}/settings/system`, formData, {
          headers: { Authorization: `Bearer ${token}` }
        });
      }
      showMessage('Setting saved successfully');
      setEditMode(null);
      fetchSettings();
    } catch (error) {
      showMessage('Error saving setting', 'error');
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xl font-semibold text-white">System Settings</h3>
        <button
          onClick={() => {
            setEditMode('new');
            setFormData({ setting_key: '', setting_value: '', category: 'general', setting_type: 'string' });
          }}
          className="btn-secondary"
        >
          <Plus size={16} className="mr-1" />
          Add Setting
        </button>
      </div>

      {editMode === 'new' && (
        <div className="bg-gray-800 p-4 rounded-lg mb-4">
          <input
            type="text"
            placeholder="Setting Key"
            value={formData.setting_key || ''}
            onChange={(e) => setFormData({ ...formData, setting_key: e.target.value })}
            className="input mb-2"
          />
          <input
            type="text"
            placeholder="Setting Value"
            value={formData.setting_value || ''}
            onChange={(e) => setFormData({ ...formData, setting_value: e.target.value })}
            className="input mb-2"
          />
          <select
            value={formData.category || 'general'}
            onChange={(e) => setFormData({ ...formData, category: e.target.value })}
            className="input mb-2"
          >
            <option value="general">General</option>
            <option value="payroll">Payroll</option>
            <option value="finance">Finance</option>
            <option value="hr">HR</option>
            <option value="inventory">Inventory</option>
          </select>
          <div className="flex space-x-2">
            <button onClick={() => handleSave({})} className="btn-primary">
              <Save size={16} className="mr-1" />
              Save
            </button>
            <button onClick={() => setEditMode(null)} className="btn-secondary">
              Cancel
            </button>
          </div>
        </div>
      )}

      <div className="space-y-2">
        {settings.map((setting) => (
          <div key={setting.id} className="bg-gray-800 p-4 rounded-lg">
            <div className="flex justify-between items-center">
              <div>
                <span className="text-erik-primary font-medium">{setting.setting_key}</span>
                <span className="text-gray-400 ml-4">{setting.setting_value}</span>
                <span className="text-gray-500 text-sm ml-4">({setting.category})</span>
              </div>
              <div className="flex space-x-2">
                <button className="text-blue-400 hover:text-blue-300">
                  <Edit2 size={16} />
                </button>
                <button className="text-red-400 hover:text-red-300">
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Leave Type Settings Component
function LeaveTypeSettings({ showMessage }) {
  const [leaveTypes, setLeaveTypes] = useState([]);
  const [configurations, setConfigurations] = useState([]);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      const [typesRes, configsRes] = await Promise.all([
        axios.get(`${API_URL}/leave-types`, { headers: { Authorization: `Bearer ${token}` } }),
        axios.get(`${API_URL}/settings/leave-configurations`, { headers: { Authorization: `Bearer ${token}` } })
      ]);
      setLeaveTypes(typesRes.data);
      setConfigurations(configsRes.data);
    } catch (error) {
      console.error('Error fetching leave types:', error);
    }
  };

  return (
    <div>
      <h3 className="text-xl font-semibold text-white mb-4">Leave Type Configuration</h3>
      <div className="space-y-4">
        {leaveTypes.map((leaveType) => {
          const config = configurations.find(c => c.leave_type_id === leaveType.id);
          return (
            <div key={leaveType.id} className="bg-gray-800 p-4 rounded-lg">
              <div className="flex justify-between items-center mb-2">
                <h4 className="text-lg font-medium text-white">{leaveType.name}</h4>
                <span className="text-sm text-gray-400">{leaveType.days_allowed} days allowed</span>
              </div>
              {config && (
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <span className="text-gray-400">Accrual: </span>
                    <span className="text-white">{config.accrual_method} ({config.accrual_rate} days)</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Approval: </span>
                    <span className="text-white">{config.requires_approval ? 'Required' : 'Not Required'}</span>
                  </div>
                  <div>
                    <span className="text-gray-400">Paid: </span>
                    <span className="text-white">{config.is_paid ? `${config.pay_percentage}%` : 'Unpaid'}</span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Tax Settings Component
function TaxSettings({ showMessage }) {
  const [taxSettings, setTaxSettings] = useState([]);

  useEffect(() => {
    fetchTaxSettings();
  }, []);

  const fetchTaxSettings = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/settings/tax`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTaxSettings(response.data);
    } catch (error) {
      console.error('Error fetching tax settings:', error);
    }
  };

  return (
    <div>
      <h3 className="text-xl font-semibold text-white mb-4">Tax & Statutory Settings</h3>
      <div className="space-y-4">
        {taxSettings.map((tax) => (
          <div key={tax.id} className="bg-gray-800 p-4 rounded-lg">
            <div className="flex justify-between items-center mb-3">
              <h4 className="text-lg font-medium text-white">{tax.tax_name}</h4>
              <span className={`px-3 py-1 rounded-full text-sm ${tax.is_active ? 'bg-green-500/20 text-green-400' : 'bg-gray-600 text-gray-400'}`}>
                {tax.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-gray-400">Type: </span>
                <span className="text-white">{tax.tax_type}</span>
              </div>
              <div>
                <span className="text-gray-400">Jurisdiction: </span>
                <span className="text-white">{tax.jurisdiction}</span>
              </div>
              {tax.employer_rate > 0 && (
                <div>
                  <span className="text-gray-400">Employer Rate: </span>
                  <span className="text-white">{tax.employer_rate}%</span>
                </div>
              )}
              {tax.employee_rate > 0 && (
                <div>
                  <span className="text-gray-400">Employee Rate: </span>
                  <span className="text-white">{tax.employee_rate}%</span>
                </div>
              )}
              {tax.applies_to && (
                <div>
                  <span className="text-gray-400">Applies To: </span>
                  <span className="text-white">{tax.applies_to}</span>
                </div>
              )}
            </div>
            {tax.tax_brackets && tax.tax_brackets.length > 0 && (
              <div className="mt-3">
                <h5 className="text-sm font-medium text-gray-300 mb-2">Tax Brackets:</h5>
                <div className="space-y-1">
                  {tax.tax_brackets.map((bracket, idx) => (
                    <div key={idx} className="text-sm text-gray-400">
                      ZMW {bracket.min.toLocaleString()} - {bracket.max.toLocaleString()}: {bracket.rate}% (Fixed: ZMW {bracket.fixed})
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// Email Templates Component
function EmailTemplates({ showMessage }) {
  const [templates, setTemplates] = useState([]);

  useEffect(() => {
    fetchTemplates();
  }, []);

  const fetchTemplates = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/settings/email-templates`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setTemplates(response.data);
    } catch (error) {
      console.error('Error fetching templates:', error);
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xl font-semibold text-white">Email Templates</h3>
        <button className="btn-secondary">
          <Plus size={16} className="mr-1" />
          Add Template
        </button>
      </div>
      <div className="space-y-3">
        {templates.map((template) => (
          <div key={template.id} className="bg-gray-800 p-4 rounded-lg">
            <div className="flex justify-between items-center">
              <div>
                <h4 className="text-white font-medium">{template.template_name}</h4>
                <p className="text-sm text-gray-400">{template.subject}</p>
                <span className="text-xs text-gray-500">Code: {template.template_code}</span>
              </div>
              <div className="flex space-x-2">
                <span className={`px-2 py-1 rounded text-xs ${template.is_system ? 'bg-blue-500/20 text-blue-400' : 'bg-gray-700 text-gray-300'}`}>
                  {template.is_system ? 'System' : 'Custom'}
                </span>
                <span className={`px-2 py-1 rounded text-xs ${template.is_active ? 'bg-green-500/20 text-green-400' : 'bg-gray-600 text-gray-400'}`}>
                  {template.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Salary Components Component
function SalaryComponents({ showMessage }) {
  const [components, setComponents] = useState([]);

  useEffect(() => {
    fetchComponents();
  }, []);

  const fetchComponents = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/settings/salary-components`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setComponents(response.data);
    } catch (error) {
      console.error('Error fetching salary components:', error);
    }
  };

  const earnings = components.filter(c => c.component_type === 'earning');
  const deductions = components.filter(c => c.component_type === 'deduction');

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xl font-semibold text-white">Salary Components</h3>
        <button className="btn-secondary">
          <Plus size={16} className="mr-1" />
          Add Component
        </button>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div>
          <h4 className="text-lg font-medium text-erik-primary mb-3">Earnings</h4>
          <div className="space-y-2">
            {earnings.map((comp) => (
              <div key={comp.id} className="bg-gray-800 p-3 rounded-lg">
                <div className="flex justify-between items-center">
                  <div>
                    <span className="text-white font-medium">{comp.component_name}</span>
                    <span className="text-gray-400 text-sm ml-2">({comp.component_code})</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    {comp.is_taxable && <span className="text-xs bg-yellow-500/20 text-yellow-400 px-2 py-1 rounded">Taxable</span>}
                    {comp.is_statutory && <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded">Statutory</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div>
          <h4 className="text-lg font-medium text-red-400 mb-3">Deductions</h4>
          <div className="space-y-2">
            {deductions.map((comp) => (
              <div key={comp.id} className="bg-gray-800 p-3 rounded-lg">
                <div className="flex justify-between items-center">
                  <div>
                    <span className="text-white font-medium">{comp.component_name}</span>
                    <span className="text-gray-400 text-sm ml-2">({comp.component_code})</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    {comp.is_statutory && <span className="text-xs bg-blue-500/20 text-blue-400 px-2 py-1 rounded">Statutory</span>}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// Approval Workflows Component
function ApprovalWorkflows({ showMessage }) {
  const [workflows, setWorkflows] = useState([]);

  useEffect(() => {
    fetchWorkflows();
  }, []);

  const fetchWorkflows = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/settings/approval-workflows`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setWorkflows(response.data);
    } catch (error) {
      console.error('Error fetching workflows:', error);
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-xl font-semibold text-white">Approval Workflows</h3>
        <button className="btn-secondary">
          <Plus size={16} className="mr-1" />
          Add Workflow
        </button>
      </div>
      <div className="space-y-3">
        {workflows.map((workflow) => (
          <div key={workflow.id} className="bg-gray-800 p-4 rounded-lg">
            <div className="flex justify-between items-center mb-2">
              <h4 className="text-white font-medium">{workflow.workflow_name}</h4>
              <span className={`px-2 py-1 rounded text-xs ${workflow.is_active ? 'bg-green-500/20 text-green-400' : 'bg-gray-600 text-gray-400'}`}>
                {workflow.is_active ? 'Active' : 'Inactive'}
              </span>
            </div>
            <div className="text-sm text-gray-400">
              <span>Entity: </span>
              <span className="text-white">{workflow.entity_type}</span>
              <span className="ml-4">Priority: </span>
              <span className="text-white">{workflow.priority}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default Settings;
