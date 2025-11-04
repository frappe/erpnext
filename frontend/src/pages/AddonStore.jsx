import { useState, useEffect } from 'react';
import { ShoppingBag, Check, Download, Star } from 'lucide-react';
import axios from 'axios';

export default function AddonStore() {
  const [addons, setAddons] = useState([]);
  const [myAddons, setMyAddons] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const token = localStorage.getItem('token');
      const [addonsRes, myAddonsRes] = await Promise.all([
        axios.get('/api/addons/marketplace', {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get('/api/addons/my-addons', {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);
      setAddons(addonsRes.data);
      setMyAddons(myAddonsRes.data);
    } catch (error) {
      console.error('Error fetching addons:', error);
    } finally {
      setLoading(false);
    }
  };

  const isActivated = (addonCode) => {
    return myAddons.some(ma => ma.addon.addon_code === addonCode);
  };

  const handleActivate = async (addonCode) => {
    try {
      const token = localStorage.getItem('token');
      await axios.post(`/api/addons/activate/${addonCode}`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert(`Addon activated successfully!`);
      fetchData();
    } catch (error) {
      console.error('Error activating addon:', error);
      alert('Failed to activate addon');
    }
  };

  const handleDeactivate = async (addonCode) => {
    if (!confirm('Are you sure you want to deactivate this addon?')) return;
    
    try {
      const token = localStorage.getItem('token');
      await axios.post(`/api/addons/deactivate/${addonCode}`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      });
      alert('Addon deactivated successfully');
      fetchData();
    } catch (error) {
      console.error('Error deactivating addon:', error);
      alert('Failed to deactivate addon');
    }
  };

  const getCategoryColor = (category) => {
    return 'from-teal-500/20 to-green-500/20';
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-teal-900 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <ShoppingBag className="w-10 h-10 text-teal-400" />
            <h1 className="text-3xl font-bold text-white">Industry Add-on Marketplace</h1>
          </div>
          <p className="text-gray-400">Activate industry-specific modules to extend ERIK ERP functionality</p>
        </div>

        <div className="bg-gray-800/50 backdrop-blur-sm rounded-lg p-6 mb-8 border border-gray-700">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="bg-gradient-to-br from-teal-500/20 to-green-500/20 backdrop-blur-sm rounded-lg p-6 border border-teal-500/30">
              <div className="flex items-center justify-between mb-2">
                <Star className="w-8 h-8 text-teal-400" />
                <span className="text-xs text-teal-300 font-medium">TOTAL ADDONS</span>
              </div>
              <p className="text-3xl font-bold text-white">{addons.length}</p>
              <p className="text-sm text-gray-400 mt-1">Available modules</p>
            </div>

            <div className="bg-gradient-to-br from-green-500/20 to-teal-500/20 backdrop-blur-sm rounded-lg p-6 border border-green-500/30">
              <div className="flex items-center justify-between mb-2">
                <Check className="w-8 h-8 text-green-400" />
                <span className="text-xs text-green-300 font-medium">ACTIVATED</span>
              </div>
              <p className="text-3xl font-bold text-white">{myAddons.length}</p>
              <p className="text-sm text-gray-400 mt-1">Currently active</p>
            </div>

            <div className="bg-gradient-to-br from-blue-500/20 to-purple-500/20 backdrop-blur-sm rounded-lg p-6 border border-blue-500/30">
              <div className="flex items-center justify-between mb-2">
                <Download className="w-8 h-8 text-blue-400" />
                <span className="text-xs text-blue-300 font-medium">AVAILABLE</span>
              </div>
              <p className="text-3xl font-bold text-white">{addons.length - myAddons.length}</p>
              <p className="text-sm text-gray-400 mt-1">Ready to activate</p>
            </div>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-teal-500 mx-auto"></div>
            <p className="text-gray-400 mt-4">Loading addons...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {addons.map((addon) => {
              const activated = isActivated(addon.addon_code);
              
              return (
                <div
                  key={addon.id}
                  className={`bg-gradient-to-br ${getCategoryColor(addon.category)} backdrop-blur-sm rounded-lg p-6 border ${
                    activated ? 'border-teal-500' : 'border-gray-700'
                  } hover:border-teal-400 transition-all`}
                >
                  <div className="flex items-start justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <div className="text-4xl">{addon.icon}</div>
                      <div>
                        <h3 className="text-lg font-bold text-white">{addon.addon_name}</h3>
                        <span className="text-xs text-gray-400">{addon.category}</span>
                      </div>
                    </div>
                    {activated && (
                      <div className="bg-teal-500/20 border border-teal-500/50 rounded-full p-2">
                        <Check className="w-4 h-4 text-teal-400" />
                      </div>
                    )}
                  </div>

                  <p className="text-sm text-gray-300 mb-4 min-h-[40px]">{addon.description}</p>

                  <div className="bg-gray-900/50 rounded-lg p-3 mb-4">
                    <p className="text-xs text-gray-400 mb-2">Key Features:</p>
                    <p className="text-xs text-gray-300">{addon.features}</p>
                  </div>

                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="text-xs text-gray-400">Pricing Model</p>
                      <p className="text-sm font-medium text-white capitalize">
                        {addon.pricing_model?.replace('_', ' ')}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs text-gray-400">Monthly Price</p>
                      <p className="text-xl font-bold text-teal-400">
                        ${addon.monthly_price?.toFixed(2)}
                      </p>
                    </div>
                  </div>

                  {activated ? (
                    <button
                      onClick={() => handleDeactivate(addon.addon_code)}
                      className="w-full px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition-all font-medium"
                    >
                      Deactivate
                    </button>
                  ) : (
                    <button
                      onClick={() => handleActivate(addon.addon_code)}
                      className="w-full px-4 py-2 bg-gradient-to-r from-teal-500 to-green-500 text-white rounded-lg hover:from-teal-600 hover:to-green-600 transition-all font-medium"
                    >
                      Activate Now
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {!loading && addons.length === 0 && (
          <div className="text-center py-12 bg-gray-800/50 backdrop-blur-sm rounded-lg border border-gray-700">
            <ShoppingBag className="w-16 h-16 text-gray-600 mx-auto mb-4" />
            <p className="text-gray-400 text-lg">No addons available</p>
          </div>
        )}
      </div>
    </div>
  );
}
