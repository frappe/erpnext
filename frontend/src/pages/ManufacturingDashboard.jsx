import { useState, useEffect } from 'react';
import { Plus, Factory, ClipboardList, Clock, CheckCircle } from 'lucide-react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function ManufacturingDashboard() {
  const [productionOrders, setProductionOrders] = useState([]);
  const [boms, setBoms] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      const [ordersRes, bomsRes] = await Promise.all([
        axios.get(`${API_URL}/api/manufacturing/production-orders`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_URL}/api/manufacturing/bom`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);
      setProductionOrders(ordersRes.data);
      setBoms(bomsRes.data);
    } catch (error) {
      console.error('Error fetching manufacturing data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      draft: 'bg-gray-500/20 text-gray-400',
      in_progress: 'bg-blue-500/20 text-blue-400',
      completed: 'bg-green-500/20 text-green-400',
      cancelled: 'bg-red-500/20 text-red-400'
    };
    return colors[status] || 'bg-gray-500/20 text-gray-400';
  };

  const draftOrders = productionOrders.filter(o => o.status === 'draft').length;
  const inProgressOrders = productionOrders.filter(o => o.status === 'in_progress').length;
  const completedOrders = productionOrders.filter(o => o.status === 'completed').length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-teal-900 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Manufacturing Dashboard</h1>
          <p className="text-gray-400">Production orders and bill of materials management</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-gradient-to-br from-teal-500/20 to-green-500/20 backdrop-blur-sm rounded-lg p-6 border border-teal-500/30">
            <div className="flex items-center justify-between mb-2">
              <Factory className="w-8 h-8 text-teal-400" />
              <span className="text-xs text-teal-300 font-medium">TOTAL ORDERS</span>
            </div>
            <p className="text-3xl font-bold text-white">{productionOrders.length}</p>
            <p className="text-sm text-gray-400 mt-1">Production orders</p>
          </div>

          <div className="bg-gradient-to-br from-gray-500/20 to-gray-600/20 backdrop-blur-sm rounded-lg p-6 border border-gray-500/30">
            <div className="flex items-center justify-between mb-2">
              <Clock className="w-8 h-8 text-gray-400" />
              <span className="text-xs text-gray-300 font-medium">DRAFT</span>
            </div>
            <p className="text-3xl font-bold text-white">{draftOrders}</p>
            <p className="text-sm text-gray-400 mt-1">Not started</p>
          </div>

          <div className="bg-gradient-to-br from-blue-500/20 to-purple-500/20 backdrop-blur-sm rounded-lg p-6 border border-blue-500/30">
            <div className="flex items-center justify-between mb-2">
              <Factory className="w-8 h-8 text-blue-400" />
              <span className="text-xs text-blue-300 font-medium">IN PROGRESS</span>
            </div>
            <p className="text-3xl font-bold text-white">{inProgressOrders}</p>
            <p className="text-sm text-gray-400 mt-1">Currently producing</p>
          </div>

          <div className="bg-gradient-to-br from-green-500/20 to-teal-500/20 backdrop-blur-sm rounded-lg p-6 border border-green-500/30">
            <div className="flex items-center justify-between mb-2">
              <CheckCircle className="w-8 h-8 text-green-400" />
              <span className="text-xs text-green-300 font-medium">COMPLETED</span>
            </div>
            <p className="text-3xl font-bold text-white">{completedOrders}</p>
            <p className="text-sm text-gray-400 mt-1">Finished orders</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-white">Production Orders</h2>
              <button className="px-4 py-2 bg-gradient-to-r from-teal-500 to-green-500 text-white rounded-lg hover:from-teal-600 hover:to-green-600 transition-all text-sm flex items-center gap-2">
                <Plus className="w-4 h-4" />
                New Order
              </button>
            </div>
            <div className="space-y-3">
              {productionOrders.slice(0, 8).map((order) => (
                <div key={order.id} className="bg-gray-900/50 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <h3 className="font-semibold text-white">{order.production_number}</h3>
                      <p className="text-sm text-gray-400">{order.product_name}</p>
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-medium ${getStatusColor(order.status)}`}>
                      {order.status?.toUpperCase()}
                    </span>
                  </div>
                  <div className="grid grid-cols-3 gap-4 mt-3 pt-3 border-t border-gray-700">
                    <div>
                      <p className="text-xs text-gray-400">Planned</p>
                      <p className="text-sm font-semibold text-white">{order.quantity_planned}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Produced</p>
                      <p className="text-sm font-semibold text-teal-400">{order.quantity_produced}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">Start Date</p>
                      <p className="text-sm text-white">{order.start_date || 'N/A'}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-white">Bill of Materials</h2>
              <button className="px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600 transition-all text-sm flex items-center gap-2">
                <Plus className="w-4 h-4" />
                New BOM
              </button>
            </div>
            <div className="space-y-3">
              {boms.map((bom) => (
                <div key={bom.id} className="bg-gray-900/50 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-3">
                      <ClipboardList className="w-5 h-5 text-blue-400" />
                      <div>
                        <h3 className="font-semibold text-white">{bom.bom_number}</h3>
                        <p className="text-sm text-gray-400">{bom.product_name}</p>
                      </div>
                    </div>
                    {bom.is_active && (
                      <span className="px-2 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400">
                        ACTIVE
                      </span>
                    )}
                  </div>
                  <div className="grid grid-cols-2 gap-4 mt-3 pt-3 border-t border-gray-700">
                    <div>
                      <p className="text-xs text-gray-400">Product Quantity</p>
                      <p className="text-sm font-semibold text-white">{bom.product_quantity}</p>
                    </div>
                    <div>
                      <p className="text-xs text-gray-400">BOM ID</p>
                      <p className="text-sm text-gray-400">#{bom.id.slice(0, 8)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {loading && (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-500 mx-auto"></div>
            <p className="text-gray-400 mt-4">Loading manufacturing data...</p>
          </div>
        )}

        {!loading && productionOrders.length === 0 && boms.length === 0 && (
          <div className="text-center py-12 bg-gray-800/50 backdrop-blur-sm rounded-lg border border-gray-700">
            <Factory className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400 text-lg">No production data yet</p>
            <p className="text-gray-500 text-sm mt-2">Create BOMs and production orders to start manufacturing</p>
          </div>
        )}
      </div>
    </div>
  );
}
