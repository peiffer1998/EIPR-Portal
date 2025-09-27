import axios from 'axios';

import { emit } from '../telemetry/telemetry';
import { toast } from '../ui/Toast';
import { TOKEN_STORAGE_KEY } from './storage';

const STAFF_TOKEN_STORAGE_KEY = 'eipr.staff.token';

const baseURL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL,
});

const getStoredToken = (): string | null => {
  if (typeof localStorage === 'undefined') return null;

  const staffToken = localStorage.getItem(STAFF_TOKEN_STORAGE_KEY);
  if (staffToken) return staffToken;

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

api.interceptors.response.use(
  (res) => {
    const reqId =
      res.headers?.['x-request-id'] ??
      res.headers?.['x-requestid'] ??
      res.headers?.['x-request_id'];
    if (reqId) {
      (res as any).requestId = reqId;
    }
    return res;
  },
  (error) => {
    const response = error?.response;
    const reqId =
      response?.headers?.['x-request-id'] ??
      response?.headers?.['x-requestid'] ??
      response?.headers?.['x-request_id'];
    const message =
      response?.data?.detail ?? error?.message ?? 'Request failed';
    const status = response?.status;

    if (reqId) (error as any).requestId = reqId;

    emit({
      ts: Date.now(),
      type: 'http.error',
      requestId: reqId,
      message,
      meta: {
        url: error?.config?.url,
        method: error?.config?.method,
        status,
      },
    });

    toast(`${message}${reqId ? ` • Request-ID ${reqId}` : ''}`, 'error');
    return Promise.reject(error);
  },
);

export default api;
