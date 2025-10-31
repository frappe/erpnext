import { useState, useEffect } from 'react'
import { Plus, Smartphone, TrendingUp, TrendingDown, Clock } from 'lucide-react'
import api from '../services/api'

export default function MobileMoney() {
  const [providers, setProviders] = useState([])
  const [transactions, setTransactions] = useState([])
  const [showProviderModal, setShowProviderModal] = useState(false)
  const [showTransactionModal, setShowTransactionModal] = useState(false)
  const [loading, setLoading] = useState(true)
  
  const [providerForm, setProviderForm] = useState({
    provider_name: '',
    provider_code: 'MTN',
    api_key: '',
    api_secret: '',
    merchant_id: ''
  })
  
  const [transactionForm, setTransactionForm] = useState({
    provider_id: '',
    transaction_type: 'collection',
    phone_number: '',
    amount: 0,
    customer_name: '',
    description: ''
  })

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [providersRes, transactionsRes] = await Promise.all([
        api.get('/api/mobile-money/providers'),
        api.get('/api/mobile-money/transactions')
      ])
      setProviders(providersRes.data)
      setTransactions(transactionsRes.data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching mobile money data:', error)
      setLoading(false)
    }
  }

  const createProvider = async (e) => {
    e.preventDefault()
    try {
      await api.post('/api/mobile-money/providers', providerForm)
      setShowProviderModal(false)
      setProviderForm({ provider_name: '', provider_code: 'MTN', api_key: '', api_secret: '', merchant_id: '' })
      fetchData()
    } catch (error) {
      console.error('Error creating provider:', error)
      alert('Failed to create provider')
    }
  }

  const createTransaction = async (e) => {
    e.preventDefault()
    try {
      await api.post('/api/mobile-money/transactions', transactionForm)
      setShowTransactionModal(false)
      setTransactionForm({ provider_id: '', transaction_type: 'collection', phone_number: '', amount: 0, customer_name: '', description: '' })
      fetchData()
    } catch (error) {
      console.error('Error creating transaction:', error)
      alert('Failed to create transaction')
    }
  }

  if (loading) return <div className="p-8 text-white">Loading...</div>

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Mobile Money</h1>
        <p className="text-gray-400">Manage MTN, Airtel, and Zamtel Money payments</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <Smartphone className="w-8 h-8 opacity-80" />
            <span className="text-3xl font-bold">{providers.length}</span>
          </div>
          <p className="text-sm opacity-90">Active Providers</p>
        </div>

        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <TrendingUp className="w-8 h-8 opacity-80" />
            <span className="text-3xl font-bold">{transactions.filter(t => t.transaction_type === 'collection').length}</span>
          </div>
          <p className="text-sm opacity-90">Collections</p>
        </div>

        <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <TrendingDown className="w-8 h-8 opacity-80" />
            <span className="text-3xl font-bold">{transactions.filter(t => t.transaction_type === 'disbursement').length}</span>
          </div>
          <p className="text-sm opacity-90">Disbursements</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-erik-light/30 backdrop-blur-lg rounded-xl p-6 border border-erik-primary/30">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-white">Providers</h2>
            <button
              onClick={() => setShowProviderModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-erik-primary text-white rounded-lg hover:bg-erik-primary/90"
            >
              <Plus className="w-4 h-4" /> Add Provider
            </button>
          </div>

          <div className="space-y-4">
            {providers.map((provider) => (
              <div key={provider.id} className="bg-erik-dark/50 rounded-lg p-4 border border-gray-700">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-white font-medium">{provider.provider_name}</h3>
                    <p className="text-gray-400 text-sm">{provider.provider_code}</p>
                  </div>
                  <span className={`px-3 py-1 rounded-full text-xs ${provider.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                    {provider.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
            ))}
            {providers.length === 0 && (
              <p className="text-gray-400 text-center py-8">No providers configured yet</p>
            )}
          </div>
        </div>

        <div className="bg-erik-light/30 backdrop-blur-lg rounded-xl p-6 border border-erik-primary/30">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-white">Recent Transactions</h2>
            <button
              onClick={() => setShowTransactionModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-erik-primary text-white rounded-lg hover:bg-erik-primary/90"
              disabled={providers.length === 0}
            >
              <Plus className="w-4 h-4" /> New Transaction
            </button>
          </div>

          <div className="space-y-4 max-h-96 overflow-y-auto">
            {transactions.slice(0, 10).map((tx) => (
              <div key={tx.id} className="bg-erik-dark/50 rounded-lg p-4 border border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-white font-medium">{tx.transaction_ref}</span>
                  <span className={`px-2 py-1 rounded text-xs ${tx.status === 'completed' ? 'bg-green-500/20 text-green-400' : tx.status === 'pending' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'}`}>
                    {tx.status}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <p className="text-gray-400">Phone:</p>
                    <p className="text-white">{tx.phone_number}</p>
                  </div>
                  <div>
                    <p className="text-gray-400">Amount:</p>
                    <p className="text-erik-primary font-medium">ZMW {tx.amount.toFixed(2)}</p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-gray-400 text-xs flex items-center gap-1">
                      <Clock className="w-3 h-3" /> {new Date(tx.created_at).toLocaleString()}
                    </p>
                  </div>
                </div>
              </div>
            ))}
            {transactions.length === 0 && (
              <p className="text-gray-400 text-center py-8">No transactions yet</p>
            )}
          </div>
        </div>
      </div>

      {showProviderModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-erik-dark rounded-xl p-8 max-w-md w-full border border-erik-primary/30">
            <h2 className="text-2xl font-bold text-white mb-6">Add Mobile Money Provider</h2>
            <form onSubmit={createProvider} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Provider Name</label>
                <input
                  type="text"
                  value={providerForm.provider_name}
                  onChange={(e) => setProviderForm({...providerForm, provider_name: e.target.value})}
                  className="w-full bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Provider</label>
                <select
                  value={providerForm.provider_code}
                  onChange={(e) => setProviderForm({...providerForm, provider_code: e.target.value})}
                  className="w-full bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                >
                  <option value="MTN">MTN Mobile Money</option>
                  <option value="AIRTEL">Airtel Money</option>
                  <option value="ZAMTEL">Zamtel Kwacha</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Merchant ID</label>
                <input
                  type="text"
                  value={providerForm.merchant_id}
                  onChange={(e) => setProviderForm({...providerForm, merchant_id: e.target.value})}
                  className="w-full bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                />
              </div>
              <div className="flex gap-4 mt-6">
                <button
                  type="button"
                  onClick={() => setShowProviderModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-erik-primary text-white rounded-lg hover:bg-erik-primary/90"
                >
                  Add Provider
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showTransactionModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-erik-dark rounded-xl p-8 max-w-md w-full border border-erik-primary/30">
            <h2 className="text-2xl font-bold text-white mb-6">New Transaction</h2>
            <form onSubmit={createTransaction} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Provider</label>
                <select
                  value={transactionForm.provider_id}
                  onChange={(e) => setTransactionForm({...transactionForm, provider_id: e.target.value})}
                  className="w-full bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                  required
                >
                  <option value="">Select Provider</option>
                  {providers.map(p => (
                    <option key={p.id} value={p.id}>{p.provider_name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Type</label>
                <select
                  value={transactionForm.transaction_type}
                  onChange={(e) => setTransactionForm({...transactionForm, transaction_type: e.target.value})}
                  className="w-full bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                >
                  <option value="collection">Collection (Receive Payment)</option>
                  <option value="disbursement">Disbursement (Send Payment)</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Phone Number</label>
                <input
                  type="text"
                  value={transactionForm.phone_number}
                  onChange={(e) => setTransactionForm({...transactionForm, phone_number: e.target.value})}
                  className="w-full bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                  placeholder="260xxxxxxxxx"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Amount (ZMW)</label>
                <input
                  type="number"
                  step="0.01"
                  value={transactionForm.amount}
                  onChange={(e) => setTransactionForm({...transactionForm, amount: parseFloat(e.target.value)})}
                  className="w-full bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Customer Name</label>
                <input
                  type="text"
                  value={transactionForm.customer_name}
                  onChange={(e) => setTransactionForm({...transactionForm, customer_name: e.target.value})}
                  className="w-full bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                />
              </div>
              <div className="flex gap-4 mt-6">
                <button
                  type="button"
                  onClick={() => setShowTransactionModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-erik-primary text-white rounded-lg hover:bg-erik-primary/90"
                >
                  Process
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
