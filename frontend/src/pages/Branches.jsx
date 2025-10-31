import { useState, useEffect } from 'react'
import { Plus, Building2, TrendingUp, Package } from 'lucide-react'
import api from '../services/api'

export default function Branches() {
  const [branches, setBranches] = useState([])
  const [transfers, setTransfers] = useState([])
  const [employees, setEmployees] = useState([])
  const [products, setProducts] = useState([])
  const [showBranchModal, setShowBranchModal] = useState(false)
  const [showTransferModal, setShowTransferModal] = useState(false)
  const [loading, setLoading] = useState(true)
  
  const [branchForm, setBranchForm] = useState({
    branch_code: '',
    branch_name: '',
    address: '',
    city: '',
    phone: '',
    email: '',
    manager_id: '',
    is_main_branch: false
  })
  
  const [transferForm, setTransferForm] = useState({
    from_branch_id: '',
    to_branch_id: '',
    transfer_date: new Date().toISOString().split('T')[0],
    lines: [{ product_id: '', quantity: 0 }],
    notes: ''
  })

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [branchesRes, transfersRes, employeesRes, productsRes] = await Promise.all([
        api.get('/api/branches'),
        api.get('/api/branch-transfers'),
        api.get('/api/employees'),
        api.get('/api/products')
      ])
      setBranches(branchesRes.data)
      setTransfers(transfersRes.data)
      setEmployees(employeesRes.data)
      setProducts(productsRes.data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching branch data:', error)
      setLoading(false)
    }
  }

  const createBranch = async (e) => {
    e.preventDefault()
    try {
      await api.post('/api/branches', branchForm)
      setShowBranchModal(false)
      setBranchForm({ branch_code: '', branch_name: '', address: '', city: '', phone: '', email: '', manager_id: '', is_main_branch: false })
      fetchData()
    } catch (error) {
      console.error('Error creating branch:', error)
      alert('Failed to create branch')
    }
  }

  const createTransfer = async (e) => {
    e.preventDefault()
    try {
      await api.post('/api/branch-transfers', transferForm)
      setShowTransferModal(false)
      setTransferForm({ from_branch_id: '', to_branch_id: '', transfer_date: new Date().toISOString().split('T')[0], lines: [{ product_id: '', quantity: 0 }], notes: '' })
      fetchData()
    } catch (error) {
      console.error('Error creating transfer:', error)
      alert('Failed to create transfer')
    }
  }

  const addTransferLine = () => {
    setTransferForm({
      ...transferForm,
      lines: [...transferForm.lines, { product_id: '', quantity: 0 }]
    })
  }

  if (loading) return <div className="p-8 text-white">Loading...</div>

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Multi-Branch Management</h1>
        <p className="text-gray-400">Manage branches and inter-branch stock transfers</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <Building2 className="w-8 h-8 opacity-80" />
            <span className="text-3xl font-bold">{branches.length}</span>
          </div>
          <p className="text-sm opacity-90">Total Branches</p>
        </div>

        <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <TrendingUp className="w-8 h-8 opacity-80" />
            <span className="text-3xl font-bold">{branches.filter(b => b.is_active).length}</span>
          </div>
          <p className="text-sm opacity-90">Active Branches</p>
        </div>

        <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <Package className="w-8 h-8 opacity-80" />
            <span className="text-3xl font-bold">{transfers.length}</span>
          </div>
          <p className="text-sm opacity-90">Total Transfers</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-erik-light/30 backdrop-blur-lg rounded-xl p-6 border border-erik-primary/30">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-white">Branches</h2>
            <button
              onClick={() => setShowBranchModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-erik-primary text-white rounded-lg hover:bg-erik-primary/90"
            >
              <Plus className="w-4 h-4" /> Add Branch
            </button>
          </div>

          <div className="space-y-4">
            {branches.map((branch) => (
              <div key={branch.id} className="bg-erik-dark/50 rounded-lg p-4 border border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <div>
                    <h3 className="text-white font-medium">{branch.branch_name}</h3>
                    <p className="text-gray-400 text-sm">{branch.branch_code}</p>
                  </div>
                  <div className="flex gap-2">
                    {branch.is_main_branch && (
                      <span className="px-2 py-1 rounded text-xs bg-yellow-500/20 text-yellow-400">Main</span>
                    )}
                    <span className={`px-2 py-1 rounded text-xs ${branch.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                      {branch.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </div>
                </div>
                {branch.city && (
                  <p className="text-gray-400 text-sm">{branch.city}</p>
                )}
              </div>
            ))}
            {branches.length === 0 && (
              <p className="text-gray-400 text-center py-8">No branches yet</p>
            )}
          </div>
        </div>

        <div className="bg-erik-light/30 backdrop-blur-lg rounded-xl p-6 border border-erik-primary/30">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-white">Stock Transfers</h2>
            <button
              onClick={() => setShowTransferModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-erik-primary text-white rounded-lg hover:bg-erik-primary/90"
              disabled={branches.length < 2}
            >
              <Plus className="w-4 h-4" /> New Transfer
            </button>
          </div>

          <div className="space-y-4 max-h-96 overflow-y-auto">
            {transfers.slice(0, 10).map((transfer) => (
              <div key={transfer.id} className="bg-erik-dark/50 rounded-lg p-4 border border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-white font-medium">{transfer.transfer_number}</span>
                  <span className={`px-2 py-1 rounded text-xs ${
                    transfer.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                    transfer.status === 'pending' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-blue-500/20 text-blue-400'
                  }`}>
                    {transfer.status}
                  </span>
                </div>
                <div className="text-sm text-gray-400">
                  <p>Date: {new Date(transfer.transfer_date).toLocaleDateString()}</p>
                </div>
              </div>
            ))}
            {transfers.length === 0 && (
              <p className="text-gray-400 text-center py-8">No transfers yet</p>
            )}
          </div>
        </div>
      </div>

      {showBranchModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 overflow-y-auto">
          <div className="bg-erik-dark rounded-xl p-8 max-w-md w-full border border-erik-primary/30 my-8">
            <h2 className="text-2xl font-bold text-white mb-6">Add New Branch</h2>
            <form onSubmit={createBranch} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Branch Code</label>
                <input
                  type="text"
                  value={branchForm.branch_code}
                  onChange={(e) => setBranchForm({...branchForm, branch_code: e.target.value})}
                  className="w-full bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Branch Name</label>
                <input
                  type="text"
                  value={branchForm.branch_name}
                  onChange={(e) => setBranchForm({...branchForm, branch_name: e.target.value})}
                  className="w-full bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">City</label>
                <input
                  type="text"
                  value={branchForm.city}
                  onChange={(e) => setBranchForm({...branchForm, city: e.target.value})}
                  className="w-full bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Manager</label>
                <select
                  value={branchForm.manager_id}
                  onChange={(e) => setBranchForm({...branchForm, manager_id: e.target.value})}
                  className="w-full bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                >
                  <option value="">Select Manager</option>
                  {employees.map(emp => (
                    <option key={emp.id} value={emp.id}>{emp.first_name} {emp.last_name}</option>
                  ))}
                </select>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={branchForm.is_main_branch}
                  onChange={(e) => setBranchForm({...branchForm, is_main_branch: e.target.checked})}
                  className="w-4 h-4"
                />
                <label className="text-sm text-gray-300">Main Branch</label>
              </div>
              <div className="flex gap-4 mt-6">
                <button
                  type="button"
                  onClick={() => setShowBranchModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-erik-primary text-white rounded-lg hover:bg-erik-primary/90"
                >
                  Add Branch
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showTransferModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 overflow-y-auto">
          <div className="bg-erik-dark rounded-xl p-8 max-w-2xl w-full border border-erik-primary/30 my-8">
            <h2 className="text-2xl font-bold text-white mb-6">New Stock Transfer</h2>
            <form onSubmit={createTransfer} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">From Branch</label>
                  <select
                    value={transferForm.from_branch_id}
                    onChange={(e) => setTransferForm({...transferForm, from_branch_id: e.target.value})}
                    className="w-full bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                    required
                  >
                    <option value="">Select Branch</option>
                    {branches.map(b => (
                      <option key={b.id} value={b.id}>{b.branch_name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">To Branch</label>
                  <select
                    value={transferForm.to_branch_id}
                    onChange={(e) => setTransferForm({...transferForm, to_branch_id: e.target.value})}
                    className="w-full bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                    required
                  >
                    <option value="">Select Branch</option>
                    {branches.map(b => (
                      <option key={b.id} value={b.id}>{b.branch_name}</option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Transfer Date</label>
                <input
                  type="date"
                  value={transferForm.transfer_date}
                  onChange={(e) => setTransferForm({...transferForm, transfer_date: e.target.value})}
                  className="w-full bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Products</label>
                {transferForm.lines.map((line, index) => (
                  <div key={index} className="grid grid-cols-2 gap-4 mb-2">
                    <select
                      value={line.product_id}
                      onChange={(e) => {
                        const newLines = [...transferForm.lines]
                        newLines[index].product_id = e.target.value
                        setTransferForm({...transferForm, lines: newLines})
                      }}
                      className="bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                      required
                    >
                      <option value="">Select Product</option>
                      {products.map(p => (
                        <option key={p.id} value={p.id}>{p.name}</option>
                      ))}
                    </select>
                    <input
                      type="number"
                      placeholder="Quantity"
                      value={line.quantity}
                      onChange={(e) => {
                        const newLines = [...transferForm.lines]
                        newLines[index].quantity = parseFloat(e.target.value)
                        setTransferForm({...transferForm, lines: newLines})
                      }}
                      className="bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                      required
                    />
                  </div>
                ))}
                <button
                  type="button"
                  onClick={addTransferLine}
                  className="text-erik-primary text-sm hover:underline"
                >
                  + Add Product
                </button>
              </div>
              <div className="flex gap-4 mt-6">
                <button
                  type="button"
                  onClick={() => setShowTransferModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-erik-primary text-white rounded-lg hover:bg-erik-primary/90"
                >
                  Create Transfer
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
