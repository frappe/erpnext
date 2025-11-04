import { useState, useEffect } from 'react';
import { Plus, Search, Eye, CheckCircle, Clock, FileText } from 'lucide-react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function SalesOrders() {
  const [orders, setOrders] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showModal, setShowModal] = useState(false);
  const [orderLines, setOrderLines] = useState([{ product_id: '', quantity: 1, unit_price: 0 }]);
  const [formData, setFormData] = useState({
    customer_id: '',
    order_date: new Date().toISOString().split('T')[0],
    delivery_date: '',
    notes: ''
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      const [ordersRes, customersRes, productsRes] = await Promise.all([
        axios.get(`${API_URL}/api/sales/orders`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_URL}/api/sales/customers`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_URL}/api/inventory/products`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);
      setOrders(ordersRes.data);
      setCustomers(customersRes.data);
      setProducts(productsRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const addLine = () => {
    setOrderLines([...orderLines, { product_id: '', quantity: 1, unit_price: 0 }]);
  };

  const removeLine = (index) => {
    setOrderLines(orderLines.filter((_, i) => i !== index));
  };

  const updateLine = (index, field, value) => {
    const newLines = [...orderLines];
    newLines[index][field] = value;
    
    if (field === 'product_id' && value) {
      const product = products.find(p => p.id === value);
      if (product) {
        newLines[index].unit_price = product.selling_price || 0;
      }
    }
    
    setOrderLines(newLines);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/api/sales/orders`, {
        ...formData,
        lines: orderLines
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setShowModal(false);
      fetchData();
      setFormData({
        customer_id: '',
        order_date: new Date().toISOString().split('T')[0],
        delivery_date: '',
        notes: ''
      });
      setOrderLines([{ product_id: '', quantity: 1, unit_price: 0 }]);
    } catch (error) {
      console.error('Error creating order:', error);
      alert('Failed to create sales order');
    }
  };

  const confirmOrder = async (orderId) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/api/sales/orders/${orderId}/confirm`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchData();
    } catch (error) {
      console.error('Error confirming order:', error);
      alert('Failed to confirm order');
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      draft: 'bg-gray-500/20 text-gray-400',
      confirmed: 'bg-teal-500/20 text-teal-400',
      delivered: 'bg-green-500/20 text-green-400',
      cancelled: 'bg-red-500/20 text-red-400'
    };
    return colors[status] || 'bg-gray-500/20 text-gray-400';
  };

  const totalAmount = orderLines.reduce((sum, line) => sum + (line.quantity * line.unit_price), 0);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-teal-900 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Sales Orders</h1>
          <p className="text-gray-400">Create and manage customer orders</p>
        </div>

        <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 mb-6 border border-gray-700">
          <div className="flex justify-between items-center">
            <div className="flex gap-4">
              <div className="bg-gray-900/50 px-4 py-3 rounded-lg">
                <p className="text-xs text-gray-400 mb-1">Total Orders</p>
                <p className="text-2xl font-bold text-white">{orders.length}</p>
              </div>
              <div className="bg-gray-900/50 px-4 py-3 rounded-lg">
                <p className="text-xs text-gray-400 mb-1">Draft</p>
                <p className="text-2xl font-bold text-gray-400">
                  {orders.filter(o => o.status === 'draft').length}
                </p>
              </div>
              <div className="bg-gray-900/50 px-4 py-3 rounded-lg">
                <p className="text-xs text-gray-400 mb-1">Confirmed</p>
                <p className="text-2xl font-bold text-teal-400">
                  {orders.filter(o => o.status === 'confirmed').length}
                </p>
              </div>
            </div>
            <button
              onClick={() => setShowModal(true)}
              className="flex items-center gap-2 px-6 py-2 bg-gradient-to-r from-teal-500 to-green-500 text-white rounded-lg hover:from-teal-600 hover:to-green-600 transition-all"
            >
              <Plus className="w-5 h-5" />
              New Sales Order
            </button>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-500 mx-auto"></div>
            <p className="text-gray-400 mt-4">Loading orders...</p>
          </div>
        ) : (
          <div className="space-y-4">
            {orders.map((order) => (
              <div
                key={order.id}
                className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700 hover:border-teal-500 transition-all"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <FileText className="w-6 h-6 text-teal-400" />
                      <h3 className="text-xl font-semibold text-white">{order.order_number}</h3>
                      <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(order.status)}`}>
                        {order.status?.toUpperCase()}
                      </span>
                    </div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                      <div>
                        <p className="text-xs text-gray-400 mb-1">Customer</p>
                        <p className="text-sm text-white">{order.customer_name || 'N/A'}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400 mb-1">Order Date</p>
                        <p className="text-sm text-white">{order.order_date || 'N/A'}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400 mb-1">Total Amount</p>
                        <p className="text-sm font-semibold text-teal-400">
                          ZMW {order.total_amount?.toLocaleString() || 0}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-400 mb-1">Items</p>
                        <p className="text-sm text-white">{order.line_count || 0} items</p>
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {order.status === 'draft' && (
                      <button
                        onClick={() => confirmOrder(order.id)}
                        className="px-4 py-2 bg-teal-500/20 text-teal-400 rounded-lg hover:bg-teal-500/30 transition-all flex items-center gap-2"
                      >
                        <CheckCircle className="w-4 h-4" />
                        Confirm
                      </button>
                    )}
                    <button className="px-4 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-all">
                      <Eye className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {!loading && orders.length === 0 && (
          <div className="text-center py-12 bg-gray-800/50 backdrop-blur-sm rounded-lg border border-gray-700">
            <p className="text-gray-400 text-lg">No sales orders yet</p>
            <p className="text-gray-500 text-sm mt-2">Create your first sales order to get started</p>
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4 z-50 overflow-y-auto">
          <div className="bg-gray-800 rounded-lg p-6 max-w-4xl w-full my-8 border border-gray-700">
            <h2 className="text-2xl font-bold text-white mb-6">Create Sales Order</h2>
            
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Customer *
                  </label>
                  <select
                    required
                    value={formData.customer_id}
                    onChange={(e) => setFormData({ ...formData, customer_id: e.target.value })}
                    className="w-full px-4 py-2 bg-gray-900/50 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                  >
                    <option value="">Select Customer</option>
                    {customers.map(c => (
                      <option key={c.id} value={c.id}>{c.customer_name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Order Date
                  </label>
                  <input
                    type="date"
                    value={formData.order_date}
                    onChange={(e) => setFormData({ ...formData, order_date: e.target.value })}
                    className="w-full px-4 py-2 bg-gray-900/50 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Delivery Date
                  </label>
                  <input
                    type="date"
                    value={formData.delivery_date}
                    onChange={(e) => setFormData({ ...formData, delivery_date: e.target.value })}
                    className="w-full px-4 py-2 bg-gray-900/50 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between mb-3">
                  <label className="block text-sm font-medium text-gray-300">
                    Order Lines
                  </label>
                  <button
                    type="button"
                    onClick={addLine}
                    className="text-teal-400 hover:text-teal-300 text-sm flex items-center gap-1"
                  >
                    <Plus className="w-4 h-4" />
                    Add Line
                  </button>
                </div>
                <div className="space-y-2">
                  {orderLines.map((line, index) => (
                    <div key={index} className="flex gap-2 items-start">
                      <select
                        value={line.product_id}
                        onChange={(e) => updateLine(index, 'product_id', e.target.value)}
                        className="flex-1 px-3 py-2 bg-gray-900/50 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                        required
                      >
                        <option value="">Select Product</option>
                        {products.map(p => (
                          <option key={p.id} value={p.id}>{p.product_name}</option>
                        ))}
                      </select>
                      <input
                        type="number"
                        placeholder="Qty"
                        value={line.quantity}
                        onChange={(e) => updateLine(index, 'quantity', parseFloat(e.target.value))}
                        className="w-20 px-3 py-2 bg-gray-900/50 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                        min="1"
                        required
                      />
                      <input
                        type="number"
                        placeholder="Price"
                        value={line.unit_price}
                        onChange={(e) => updateLine(index, 'unit_price', parseFloat(e.target.value))}
                        className="w-28 px-3 py-2 bg-gray-900/50 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"
                        step="0.01"
                        required
                      />
                      <div className="w-32 px-3 py-2 bg-gray-900/30 border border-gray-700 rounded-lg text-gray-400 text-sm">
                        {(line.quantity * line.unit_price).toFixed(2)}
                      </div>
                      {orderLines.length > 1 && (
                        <button
                          type="button"
                          onClick={() => removeLine(index)}
                          className="px-3 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30"
                        >
                          ×
                        </button>
                      )}
                    </div>
                  ))}
                </div>
                <div className="mt-4 p-4 bg-gray-900/50 rounded-lg flex justify-between items-center">
                  <span className="text-gray-300 font-medium">Total Amount (excl. VAT)</span>
                  <span className="text-2xl font-bold text-teal-400">ZMW {totalAmount.toFixed(2)}</span>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">
                  Notes
                </label>
                <textarea
                  value={formData.notes}
                  onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
                  rows="3"
                  className="w-full px-4 py-2 bg-gray-900/50 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-teal-500"
                />
              </div>

              <div className="flex gap-4 pt-4">
                <button
                  type="submit"
                  className="flex-1 px-6 py-2 bg-gradient-to-r from-teal-500 to-green-500 text-white rounded-lg hover:from-teal-600 hover:to-green-600 transition-all"
                >
                  Create Sales Order
                </button>
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="flex-1 px-6 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600 transition-all"
                >
                  Cancel
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
