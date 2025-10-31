import React, { useState, useEffect } from 'react';
import { Plus, User } from 'lucide-react';
import { employees } from '../services/api';

function Employees() {
  const [employeeList, setEmployeeList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({
    employee_no: '',
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    position: '',
    department: '',
    salary_base: 0,
    date_joined: new Date().toISOString().split('T')[0],
  });

  const loadEmployees = () => {
    employees.getAll()
      .then(response => {
        setEmployeeList(response.data);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  };

  useEffect(() => {
    loadEmployees();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      await employees.create(formData);
      setShowForm(false);
      setFormData({
        employee_no: '',
        first_name: '',
        last_name: '',
        email: '',
        phone: '',
        position: '',
        department: '',
        salary_base: 0,
        date_joined: new Date().toISOString().split('T')[0],
      });
      loadEmployees();
    } catch (error) {
      alert('Failed to create employee');
    }
  };

  if (loading) {
    return <div className="text-erik-primary">Loading...</div>;
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Employees</h1>
          <p className="text-gray-400">Manage your workforce</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          className="btn-primary flex items-center"
        >
          <Plus size={20} className="mr-2" />
          Add Employee
        </button>
      </div>

      {showForm && (
        <div className="card mb-6">
          <h3 className="text-xl font-semibold text-white mb-4">New Employee</h3>
          <form onSubmit={handleSubmit} className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Employee Number
              </label>
              <input
                type="text"
                required
                className="input-field"
                value={formData.employee_no}
                onChange={(e) => setFormData({ ...formData, employee_no: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                First Name
              </label>
              <input
                type="text"
                required
                className="input-field"
                value={formData.first_name}
                onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Last Name
              </label>
              <input
                type="text"
                required
                className="input-field"
                value={formData.last_name}
                onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Email
              </label>
              <input
                type="email"
                className="input-field"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Position
              </label>
              <input
                type="text"
                required
                className="input-field"
                value={formData.position}
                onChange={(e) => setFormData({ ...formData, position: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Department
              </label>
              <input
                type="text"
                required
                className="input-field"
                value={formData.department}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Base Salary
              </label>
              <input
                type="number"
                step="0.01"
                required
                className="input-field"
                value={formData.salary_base}
                onChange={(e) => setFormData({ ...formData, salary_base: parseFloat(e.target.value) })}
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-300 mb-2">
                Date Joined
              </label>
              <input
                type="date"
                required
                className="input-field"
                value={formData.date_joined}
                onChange={(e) => setFormData({ ...formData, date_joined: e.target.value })}
              />
            </div>
            <div className="col-span-2 flex space-x-4">
              <button type="submit" className="btn-primary">
                Create Employee
              </button>
              <button
                type="button"
                onClick={() => setShowForm(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {employeeList.length === 0 ? (
          <div className="col-span-3 text-center py-12 text-gray-400">
            No employees yet. Add your first employee to get started!
          </div>
        ) : (
          employeeList.map((employee) => (
            <div key={employee.id} className="card">
              <div className="flex items-start">
                <div className="bg-erik-primary/20 p-3 rounded-lg mr-4">
                  <User className="text-erik-primary" size={24} />
                </div>
                <div className="flex-1">
                  <h4 className="font-semibold text-white">
                    {employee.first_name} {employee.last_name}
                  </h4>
                  <p className="text-sm text-gray-400 mb-1">{employee.position}</p>
                  <p className="text-xs text-gray-500">{employee.department}</p>
                  <div className="mt-2">
                    <span className={`text-xs px-2 py-1 rounded ${
                      employee.employment_status === 'active' 
                        ? 'bg-green-500/20 text-green-400' 
                        : 'bg-gray-500/20 text-gray-400'
                    }`}>
                      {employee.employment_status}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default Employees;
