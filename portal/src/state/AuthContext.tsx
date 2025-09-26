import { createContext, useContext, useMemo, useState } from 'react';
import type { PropsWithChildren } from 'react';

import { readOwner, readToken, writeOwner, writeToken } from '../lib/storage';
import type { StoredOwnerSummary } from '../lib/storage';
import { logout as performLogout } from '../lib/auth';

interface AuthContextValue {
  token: string | null;
  owner: StoredOwnerSummary | null;
  isAuthenticated: boolean;
  setSession: (token: string, owner?: StoredOwnerSummary | null) => void;
  setOwner: (owner: StoredOwnerSummary | null) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export const AuthProvider = ({ children }: PropsWithChildren) => {
  const [token, setToken] = useState<string | null>(() => readToken());
  const [owner, setOwnerState] = useState<StoredOwnerSummary | null>(() => readOwner());

  const setOwner = (next: StoredOwnerSummary | null) => {
    setOwnerState(next);
    writeOwner(next);
  };

  const setSession = (nextToken: string, nextOwner?: StoredOwnerSummary | null) => {
    setToken(nextToken);
    writeToken(nextToken);
    if (typeof nextOwner !== 'undefined') {
      setOwner(nextOwner);
    }
  };

  const logout = () => {
    performLogout();
    setToken(null);
    setOwner(null);
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      owner,
      isAuthenticated: Boolean(token),
      setSession,
      setOwner,
      logout,
    }),
    [owner, token],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextValue => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
