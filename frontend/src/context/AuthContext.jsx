import { createContext, useContext, useState } from 'react';
import api from '../api';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [rep, setRep] = useState(() => {
    const saved = localStorage.getItem('rep');
    return saved ? JSON.parse(saved) : null;
  });

  const login = async (username, password) => {
    const { data } = await api.post('/login', { username, password });
    localStorage.setItem('token', data.access_token);
    const repData = { id: data.rep_id, name: data.rep_name };
    localStorage.setItem('rep', JSON.stringify(repData));
    setRep(repData);
    return data;
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('rep');
    setRep(null);
  };

  return (
    <AuthContext.Provider value={{ rep, login, logout, isAuthenticated: !!rep }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
