import React, { useState, useEffect } from 'react';
import { Bell, X, Check, Trash2, CheckCheck } from 'lucide-react';
import axios from 'axios';

const API_URL = 'http://127.0.0.1:8000/api';

function NotificationCenter() {
  const [isOpen, setIsOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchNotifications();
    }
  }, [isOpen]);

  const fetchUnreadCount = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/notifications/unread-count`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUnreadCount(response.data.unread_count);
    } catch (error) {
      console.error('Error fetching unread count:', error);
    }
  };

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/notifications?limit=20`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setNotifications(response.data);
    } catch (error) {
      console.error('Error fetching notifications:', error);
    } finally {
      setLoading(false);
    }
  };

  const markAsRead = async (notificationId) => {
    try {
      const token = localStorage.getItem('token');
      await axios.put(`${API_URL}/notifications/${notificationId}/mark-read`, null, {
        headers: { Authorization: `Bearer ${token}` },
        params: { is_read: true }
      });
      fetchNotifications();
      fetchUnreadCount();
    } catch (error) {
      console.error('Error marking as read:', error);
    }
  };

  const markAllAsRead = async () => {
    try {
      const token = localStorage.getItem('token');
      await axios.put(`${API_URL}/notifications/mark-all-read`, null, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchNotifications();
      fetchUnreadCount();
    } catch (error) {
      console.error('Error marking all as read:', error);
    }
  };

  const deleteNotification = async (notificationId) => {
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API_URL}/notifications/${notificationId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchNotifications();
      fetchUnreadCount();
    } catch (error) {
      console.error('Error deleting notification:', error);
    }
  };

  const getNotificationIcon = (type) => {
    const icons = {
      info: '💡',
      success: '✅',
      warning: '⚠️',
      error: '❌'
    };
    return icons[type] || icons.info;
  };

  const getNotificationColor = (type) => {
    const colors = {
      info: 'border-blue-500',
      success: 'border-green-500',
      warning: 'border-yellow-500',
      error: 'border-red-500'
    };
    return colors[type] || colors.info;
  };

  const formatTime = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);

    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
    
    return date.toLocaleDateString();
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-md text-erik-primary hover:bg-erik-dark/50 transition-colors"
      >
        <Bell size={20} />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center font-bold">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          
          <div className="absolute right-0 mt-2 w-96 bg-erik-light border border-gray-700 rounded-lg shadow-2xl z-50 max-h-[600px] overflow-hidden flex flex-col">
            <div className="p-4 border-b border-gray-700 flex justify-between items-center">
              <h3 className="text-lg font-semibold text-white">Notifications</h3>
              <div className="flex items-center space-x-2">
                {unreadCount > 0 && (
                  <button
                    onClick={markAllAsRead}
                    className="text-xs text-erik-primary hover:text-erik-primary/80 flex items-center"
                    title="Mark all as read"
                  >
                    <CheckCheck size={16} className="mr-1" />
                    Mark all read
                  </button>
                )}
                <button
                  onClick={() => setIsOpen(false)}
                  className="text-gray-400 hover:text-white"
                >
                  <X size={20} />
                </button>
              </div>
            </div>

            <div className="overflow-y-auto flex-1">
              {loading ? (
                <div className="p-8 text-center text-gray-400">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-erik-primary mx-auto"></div>
                  <p className="mt-2">Loading...</p>
                </div>
              ) : notifications.length === 0 ? (
                <div className="p-8 text-center text-gray-400">
                  <Bell size={48} className="mx-auto mb-4 opacity-50" />
                  <p>No notifications yet</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-700">
                  {notifications.map((notification) => (
                    <div
                      key={notification.id}
                      className={`p-4 hover:bg-erik-dark/30 transition-colors ${
                        !notification.is_read ? 'bg-erik-dark/20 border-l-4' : 'border-l-4 border-transparent'
                      } ${!notification.is_read ? getNotificationColor(notification.notification_type) : ''}`}
                    >
                      <div className="flex justify-between items-start">
                        <div className="flex-1 pr-2">
                          <div className="flex items-center space-x-2 mb-1">
                            <span className="text-lg">{getNotificationIcon(notification.notification_type)}</span>
                            <h4 className="font-medium text-white text-sm">{notification.title}</h4>
                            {!notification.is_read && (
                              <span className="h-2 w-2 bg-erik-primary rounded-full"></span>
                            )}
                          </div>
                          <p className="text-sm text-gray-400 mb-2">{notification.message}</p>
                          <div className="flex items-center justify-between">
                            <span className="text-xs text-gray-500">{formatTime(notification.created_at)}</span>
                            {notification.action_url && notification.action_label && (
                              <a
                                href={notification.action_url}
                                className="text-xs text-erik-primary hover:underline"
                                onClick={() => setIsOpen(false)}
                              >
                                {notification.action_label}
                              </a>
                            )}
                          </div>
                        </div>
                        <div className="flex flex-col space-y-1">
                          {!notification.is_read && (
                            <button
                              onClick={() => markAsRead(notification.id)}
                              className="text-green-400 hover:text-green-300 p-1"
                              title="Mark as read"
                            >
                              <Check size={16} />
                            </button>
                          )}
                          <button
                            onClick={() => deleteNotification(notification.id)}
                            className="text-red-400 hover:text-red-300 p-1"
                            title="Delete"
                          >
                            <Trash2 size={16} />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {notifications.length > 0 && (
              <div className="p-3 border-t border-gray-700 text-center">
                <button
                  onClick={() => {
                    setIsOpen(false);
                  }}
                  className="text-sm text-erik-primary hover:text-erik-primary/80"
                >
                  View All Notifications
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

export default NotificationCenter;
