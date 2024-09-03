import React, { createContext, useContext, useState, useEffect } from 'react';
import { login, logout, refreshToken } from '../utils/auth';

interface AuthContextType {
  user: any | null;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC = ({ children }) => {
  const [user, setUser] = useState<any | null>(null);

  useEffect(() => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      // TODO: Validate token and set user
    }
  }, []);

  const loginHandler = async (username: string, password: string) => {
    const userData = await login(username, password);
    setUser(userData);
  };

  const logoutHandler = () => {
    logout();
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login: loginHandler, logout: logoutHandler }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};