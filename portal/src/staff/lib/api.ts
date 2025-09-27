import { staffApi } from './client';
import type { StaffUser } from '../types';

export const staffLogin = async (
  email: string,
  password: string,
): Promise<string> => {
  const body = new URLSearchParams({
    username: email,
    password,
  });
  const { data } = await staffApi.post<{ access_token: string }>(
    '/auth/token',
    body,
    {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    },
  );
  return data.access_token;
};

export const fetchStaffProfile = async (): Promise<StaffUser> => {
  const { data } = await staffApi.get<StaffUser>('/users/me');
  return data;
};
