import { STAFF_SESSION_KEY } from './config';
import type { StaffUser } from '../types';

export interface StaffSession {
  token: string;
  user: StaffUser | null;
}

export const loadStaffSession = (): StaffSession | null => {
  if (typeof localStorage === 'undefined') return null;
  try {
    const raw = localStorage.getItem(STAFF_SESSION_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as StaffSession;
  } catch (error) {
    console.warn('Failed to parse stored staff session', error);
    localStorage.removeItem(STAFF_SESSION_KEY);
    return null;
  }
};

export const saveStaffSession = (session: StaffSession | null): void => {
  if (typeof localStorage === 'undefined') return;
  if (!session) {
    localStorage.removeItem(STAFF_SESSION_KEY);
    return;
  }
  localStorage.setItem(STAFF_SESSION_KEY, JSON.stringify(session));
};
