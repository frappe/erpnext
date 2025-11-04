import { useState, useEffect } from 'react';
import { Package, Warehouse, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function InventoryDashboard() {
  const [stockItems, setStockItems] = useState([]);
  const [warehouses, setWarehouses] = useState([]);
  const [movements, setMovements] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      const [stockRes, warehouseRes, movementRes] = await Promise.all([
        axios.get(`${API_URL}/api/inventory/stock`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_URL}/api/inventory/warehouses`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API_URL}/api/inventory/stock/movements?limit=10`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);
      setStockItems(stockRes.data);
      setWarehouses(warehouseRes.data);
      setMovements(movementRes.data);
    } catch (error) {
      console.error('Error fetching inventory data:', error);
    } finally {
      setLoading(false);
    }
  };

  const totalValue = stockItems.reduce((sum, item) => sum + (item.quantity_on_hand * item.unit_cost || 0), 0);
  const lowStockItems = stockItems.filter(item => item.quantity_on_hand < 10).length;

  const getMovementIcon = (type) => {
    return type === 'sale' || type === 'adjustment_decrease' ? 
      <TrendingDown className="w-4 h-4 text-red-400" /> : 
      <TrendingUp className="w-4 h-4 text-green-400" />;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-teal-900 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-white mb-2">Inventory Dashboard</h1>
          <p className="text-gray-400">Real-time stock levels and warehouse management</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <div className="bg-gradient-to-br from-teal-500/20 to-green-500/20 backdrop-blur-sm rounded-lg p-6 border border-teal-500/30">
            <div className="flex items-center justify-between mb-2">
              <Package className="w-8 h-8 text-teal-400" />
              <span className="text-xs text-teal-300 font-medium">TOTAL ITEMS</span>
            </div>
            <p className="text-3xl font-bold text-white">{stockItems.length}</p>
            <p className="text-sm text-gray-400 mt-1">Unique products</p>
          </div>

          <div className="bg-gradient-to-br from-blue-500/20 to-purple-500/20 backdrop-blur-sm rounded-lg p-6 border border-blue-500/30">
            <div className="flex items-center justify-between mb-2">
              <Warehouse className="w-8 h-8 text-blue-400" />
              <span className="text-xs text-blue-300 font-medium">WAREHOUSES</span>
            </div>
            <p className="text-3xl font-bold text-white">{warehouses.length}</p>
            <p className="text-sm text-gray-400 mt-1">Active locations</p>
          </div>

          <div className="bg-gradient-to-br from-orange-500/20 to-red-500/20 backdrop-blur-sm rounded-lg p-6 border border-orange-500/30">
            <div className="flex items-center justify-between mb-2">
              <AlertTriangle className="w-8 h-8 text-orange-400" />
              <span className="text-xs text-orange-300 font-medium">LOW STOCK</span>
            </div>
            <p className="text-3xl font-bold text-white">{lowStockItems}</p>
            <p className="text-sm text-gray-400 mt-1">Items need reorder</p>
          </div>

          <div className="bg-gradient-to-br from-green-500/20 to-teal-500/20 backdrop-blur-sm rounded-lg p-6 border border-green-500/30">
            <div className="flex items-center justify-between mb-2">
              <TrendingUp className="w-8 h-8 text-green-400" />
              <span className="text-xs text-green-300 font-medium">TOTAL VALUE</span>
            </div>
            <p className="text-3xl font-bold text-white">ZMW {totalValue.toLocaleString(undefined, {maximumFractionDigits: 0})}</p>
            <p className="text-sm text-gray-400 mt-1">Stock valuation</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
            <h2 className="text-xl font-bold text-white mb-4">Stock by Warehouse</h2>
            <div className="space-y-3">
              {warehouses.map((warehouse) => {
                const warehouseStock = stockItems.filter(item => item.warehouse_id === warehouse.id);
                const warehouseValue = warehouseStock.reduce((sum, item) => 
                  sum + (item.quantity_on_hand * item.unit_cost || 0), 0
                );
                
                return (
                  <div key={warehouse.id} className="bg-gray-900/50 rounded-lg p-4">
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-3">
                        <Warehouse className="w-5 h-5 text-teal-400" />
                        <div>
                          <h3 className="font-semibold text-white">{warehouse.warehouse_name}</h3>
                          <p className="text-xs text-gray-400">{warehouse.location}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-semibold text-teal-400">
                          {warehouseStock.length} items
                        </p>
                        <p className="text-xs text-gray-400">
                          ZMW {warehouseValue.toLocaleString(undefined, {maximumFractionDigits: 0})}
                        </p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
            <h2 className="text-xl font-bold text-white mb-4">Recent Stock Movements</h2>
            <div className="space-y-2">
              {movements.slice(0, 8).map((movement) => (
                <div key={movement.id} className="bg-gray-900/50 rounded-lg p-3 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {getMovementIcon(movement.movement_type)}
                    <div>
                      <p className="text-sm font-medium text-white">{movement.product_name}</p>
                      <p className="text-xs text-gray-400">
                        {movement.movement_type?.replace('_', ' ').toUpperCase()}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-white">
                      {movement.quantity > 0 ? '+' : ''}{movement.quantity}
                    </p>
                    <p className="text-xs text-gray-400">{movement.movement_date}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 border border-gray-700">
          <h2 className="text-xl font-bold text-white mb-4">Current Stock Levels</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Product</th>
                  <th className="text-left py-3 px-4 text-gray-400 font-medium">Warehouse</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">On Hand</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Reserved</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Available</th>
                  <th className="text-right py-3 px-4 text-gray-400 font-medium">Value</th>
                </tr>
              </thead>
              <tbody>
                {stockItems.slice(0, 15).map((item) => {
                  const available = item.quantity_on_hand - item.quantity_reserved;
                  const isLow = available < 10;
                  
                  return (
                    <tr key={item.id} className="border-b border-gray-700/50 hover:bg-gray-700/30 transition-colors">
                      <td className="py-3 px-4">
                        <p className="text-white font-medium">{item.product_name}</p>
                        <p className="text-xs text-gray-400">{item.product_code}</p>
                      </td>
                      <td className="py-3 px-4 text-gray-300">{item.warehouse_name}</td>
                      <td className="py-3 px-4 text-right text-white">{item.quantity_on_hand}</td>
                      <td className="py-3 px-4 text-right text-gray-400">{item.quantity_reserved}</td>
                      <td className="py-3 px-4 text-right">
                        <span className={isLow ? 'text-orange-400 font-semibold' : 'text-teal-400'}>
                          {available}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right text-white">
                        ZMW {(item.quantity_on_hand * item.unit_cost || 0).toLocaleString()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
