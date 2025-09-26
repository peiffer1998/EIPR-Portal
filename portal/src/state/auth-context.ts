import { createContext } from 'react';

import type { StoredOwnerSummary } from '../lib/storage';

export interface AuthContextValue {
  token: string | null;
  owner: StoredOwnerSummary | null;
  isAuthenticated: boolean;
  setSession: (token: string, owner?: StoredOwnerSummary | null) => void;
  setOwner: (owner: StoredOwnerSummary | null) => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);
