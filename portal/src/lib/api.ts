import axios from 'axios';

import { TOKEN_STORAGE_KEY } from './storage';

const baseURL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL,
});

const getStoredToken = (): string | null => {
  if (typeof localStorage === 'undefined') return null;
  return localStorage.getItem(TOKEN_STORAGE_KEY);
};

api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

export default api;
