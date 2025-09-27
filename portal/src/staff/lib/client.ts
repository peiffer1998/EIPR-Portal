import axios from 'axios';

import { STAFF_API_BASE_URL } from './config';

let authToken: string | null = null;

export const setStaffToken = (token: string | null) => {
  authToken = token;
};

export const clearStaffToken = () => {
  authToken = null;
};

export const staffApi = axios.create({
  baseURL: STAFF_API_BASE_URL,
});

staffApi.interceptors.request.use((config) => {
  if (authToken) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${authToken}`;
  }
  return config;
});

staffApi.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearStaffToken();
    }
    return Promise.reject(error);
  },
);
