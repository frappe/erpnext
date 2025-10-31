import { useState, useEffect } from 'react'
import { Plus, ShoppingCart, CreditCard, Receipt, Clock } from 'lucide-react'
import api from '../services/api'

export default function POS() {
  const [terminals, setTerminals] = useState([])
  const [sales, setSales] = useState([])
  const [products, setProducts] = useState([])
  const [cart, setCart] = useState([])
  const [showTerminalModal, setShowTerminalModal] = useState(false)
  const [loading, setLoading] = useState(true)
  
  const [terminalForm, setTerminalForm] = useState({
    terminal_code: '',
    terminal_name: ''
  })

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    try {
      const [terminalsRes, salesRes, productsRes] = await Promise.all([
        api.get('/api/pos/terminals'),
        api.get('/api/pos/sales'),
        api.get('/api/products')
      ])
      setTerminals(terminalsRes.data)
      setSales(salesRes.data)
      setProducts(productsRes.data)
      setLoading(false)
    } catch (error) {
      console.error('Error fetching POS data:', error)
      setLoading(false)
    }
  }

  const createTerminal = async (e) => {
    e.preventDefault()
    try {
      await api.post('/api/pos/terminals', terminalForm)
      setShowTerminalModal(false)
      setTerminalForm({ terminal_code: '', terminal_name: '' })
      fetchData()
    } catch (error) {
      console.error('Error creating terminal:', error)
      alert('Failed to create terminal')
    }
  }

  const addToCart = (product) => {
    const existing = cart.find(item => item.product_id === product.id)
    if (existing) {
      setCart(cart.map(item => 
        item.product_id === product.id 
          ? {...item, quantity: item.quantity + 1}
          : item
      ))
    } else {
      setCart([...cart, {
        product_id: product.id,
        name: product.name,
        quantity: 1,
        unit_price: product.unit_price
      }])
    }
  }

  const removeFromCart = (productId) => {
    setCart(cart.filter(item => item.product_id !== productId))
  }

  const updateQuantity = (productId, newQuantity) => {
    if (newQuantity <= 0) {
      removeFromCart(productId)
    } else {
      setCart(cart.map(item =>
        item.product_id === productId
          ? {...item, quantity: newQuantity}
          : item
      ))
    }
  }

  const getTotal = () => {
    return cart.reduce((sum, item) => sum + (item.quantity * item.unit_price), 0)
  }

  const checkout = async (paymentMethod) => {
    if (cart.length === 0) {
      alert('Cart is empty')
      return
    }

    try {
      await api.post('/api/pos/sales', {
        lines: cart,
        payment_method: paymentMethod
      })
      setCart([])
      fetchData()
      alert('Sale completed successfully!')
    } catch (error) {
      console.error('Error completing sale:', error)
      alert('Failed to complete sale')
    }
  }

  if (loading) return <div className="p-8 text-white">Loading...</div>

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-white mb-2">Point of Sale (POS)</h1>
        <p className="text-gray-400">Fast checkout and sales management</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <div className="bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <ShoppingCart className="w-8 h-8 opacity-80" />
            <span className="text-3xl font-bold">{sales.length}</span>
          </div>
          <p className="text-sm opacity-90">Total Sales</p>
        </div>

        <div className="bg-gradient-to-br from-green-500 to-green-600 rounded-xl p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <CreditCard className="w-8 h-8 opacity-80" />
            <span className="text-3xl font-bold">ZMW {sales.reduce((sum, s) => sum + s.total_amount, 0).toFixed(2)}</span>
          </div>
          <p className="text-sm opacity-90">Total Revenue</p>
        </div>

        <div className="bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <Receipt className="w-8 h-8 opacity-80" />
            <span className="text-3xl font-bold">{terminals.length}</span>
          </div>
          <p className="text-sm opacity-90">POS Terminals</p>
        </div>

        <div className="bg-gradient-to-br from-orange-500 to-orange-600 rounded-xl p-6 text-white">
          <div className="flex items-center justify-between mb-4">
            <Clock className="w-8 h-8 opacity-80" />
            <span className="text-3xl font-bold">{cart.length}</span>
          </div>
          <p className="text-sm opacity-90">Items in Cart</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 bg-erik-light/30 backdrop-blur-lg rounded-xl p-6 border border-erik-primary/30">
          <h2 className="text-xl font-bold text-white mb-6">Products</h2>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-4 max-h-96 overflow-y-auto">
            {products.map((product) => (
              <div
                key={product.id}
                onClick={() => addToCart(product)}
                className="bg-erik-dark/50 rounded-lg p-4 border border-gray-700 cursor-pointer hover:border-erik-primary transition-colors"
              >
                <h3 className="text-white font-medium mb-2">{product.name}</h3>
                <p className="text-erik-primary font-bold">ZMW {product.unit_price.toFixed(2)}</p>
                <p className="text-gray-400 text-xs mt-1">{product.code}</p>
              </div>
            ))}
            {products.length === 0 && (
              <p className="text-gray-400 col-span-full text-center py-8">No products available</p>
            )}
          </div>
        </div>

        <div className="bg-erik-light/30 backdrop-blur-lg rounded-xl p-6 border border-erik-primary/30">
          <h2 className="text-xl font-bold text-white mb-6">Cart</h2>
          
          <div className="space-y-4 mb-6 max-h-64 overflow-y-auto">
            {cart.map((item) => (
              <div key={item.product_id} className="bg-erik-dark/50 rounded-lg p-4 border border-gray-700">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-white font-medium">{item.name}</span>
                  <button
                    onClick={() => removeFromCart(item.product_id)}
                    className="text-red-400 hover:text-red-300 text-sm"
                  >
                    Remove
                  </button>
                </div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => updateQuantity(item.product_id, item.quantity - 1)}
                      className="w-6 h-6 bg-gray-600 rounded text-white hover:bg-gray-500"
                    >
                      -
                    </button>
                    <span className="text-white w-8 text-center">{item.quantity}</span>
                    <button
                      onClick={() => updateQuantity(item.product_id, item.quantity + 1)}
                      className="w-6 h-6 bg-gray-600 rounded text-white hover:bg-gray-500"
                    >
                      +
                    </button>
                  </div>
                  <span className="text-erik-primary font-bold">
                    ZMW {(item.quantity * item.unit_price).toFixed(2)}
                  </span>
                </div>
              </div>
            ))}
            {cart.length === 0 && (
              <p className="text-gray-400 text-center py-8">Cart is empty</p>
            )}
          </div>

          <div className="border-t border-gray-700 pt-4 mb-6">
            <div className="flex items-center justify-between text-xl font-bold text-white mb-4">
              <span>Total:</span>
              <span className="text-erik-primary">ZMW {getTotal().toFixed(2)}</span>
            </div>
          </div>

          <div className="space-y-3">
            <button
              onClick={() => checkout('cash')}
              disabled={cart.length === 0}
              className="w-full px-4 py-3 bg-erik-primary text-white rounded-lg hover:bg-erik-primary/90 disabled:bg-gray-600 disabled:cursor-not-allowed"
            >
              Pay Cash
            </button>
            <button
              onClick={() => checkout('mobile_money')}
              disabled={cart.length === 0}
              className="w-full px-4 py-3 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-600 disabled:cursor-not-allowed"
            >
              Pay Mobile Money
            </button>
            <button
              onClick={() => checkout('card')}
              disabled={cart.length === 0}
              className="w-full px-4 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed"
            >
              Pay Card
            </button>
          </div>
        </div>
      </div>

      <div className="mt-8 bg-erik-light/30 backdrop-blur-lg rounded-xl p-6 border border-erik-primary/30">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-bold text-white">Recent Sales</h2>
          <button
            onClick={() => setShowTerminalModal(true)}
            className="flex items-center gap-2 px-4 py-2 bg-erik-primary text-white rounded-lg hover:bg-erik-primary/90"
          >
            <Plus className="w-4 h-4" /> Add Terminal
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-white">
            <thead className="bg-erik-dark/50">
              <tr>
                <th className="px-4 py-3 text-erik-primary">Receipt</th>
                <th className="px-4 py-3 text-erik-primary">Date</th>
                <th className="px-4 py-3 text-erik-primary">Amount</th>
                <th className="px-4 py-3 text-erik-primary">Payment</th>
                <th className="px-4 py-3 text-erik-primary">Status</th>
              </tr>
            </thead>
            <tbody>
              {sales.slice(0, 10).map((sale) => (
                <tr key={sale.id} className="border-b border-gray-700 hover:bg-erik-dark/30">
                  <td className="px-4 py-3 font-medium">{sale.receipt_number}</td>
                  <td className="px-4 py-3 text-gray-300">{new Date(sale.sale_date).toLocaleString()}</td>
                  <td className="px-4 py-3 text-erik-primary font-bold">ZMW {sale.total_amount.toFixed(2)}</td>
                  <td className="px-4 py-3 text-gray-300 capitalize">{sale.payment_method.replace('_', ' ')}</td>
                  <td className="px-4 py-3">
                    <span className="px-3 py-1 rounded-full text-xs bg-green-500/20 text-green-400">
                      {sale.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {showTerminalModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-erik-dark rounded-xl p-8 max-w-md w-full border border-erik-primary/30">
            <h2 className="text-2xl font-bold text-white mb-6">Add POS Terminal</h2>
            <form onSubmit={createTerminal} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Terminal Code</label>
                <input
                  type="text"
                  value={terminalForm.terminal_code}
                  onChange={(e) => setTerminalForm({...terminalForm, terminal_code: e.target.value})}
                  className="w-full bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Terminal Name</label>
                <input
                  type="text"
                  value={terminalForm.terminal_name}
                  onChange={(e) => setTerminalForm({...terminalForm, terminal_name: e.target.value})}
                  className="w-full bg-erik-light border border-erik-primary/30 rounded-lg px-4 py-2 text-white"
                  required
                />
              </div>
              <div className="flex gap-4 mt-6">
                <button
                  type="button"
                  onClick={() => setShowTerminalModal(false)}
                  className="flex-1 px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 px-4 py-2 bg-erik-primary text-white rounded-lg hover:bg-erik-primary/90"
                >
                  Add Terminal
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
