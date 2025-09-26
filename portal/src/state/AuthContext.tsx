import { useCallback, useMemo, useState } from 'react';
import type { PropsWithChildren } from 'react';

import { readOwner, readToken, writeOwner, writeToken } from '../lib/storage';
import type { StoredOwnerSummary } from '../lib/storage';
import { logout as performLogout } from '../lib/auth';
import { AuthContext, type AuthContextValue } from './auth-context';

export const AuthProvider = ({ children }: PropsWithChildren) => {
  const [token, setToken] = useState<string | null>(() => readToken());
  const [owner, setOwnerState] = useState<StoredOwnerSummary | null>(() => readOwner());

  const setOwner = useCallback((next: StoredOwnerSummary | null) => {
    setOwnerState(next);
    writeOwner(next);
  }, []);

  const setSession = useCallback(
    (nextToken: string, nextOwner?: StoredOwnerSummary | null) => {
      setToken(nextToken);
      writeToken(nextToken);
      if (typeof nextOwner !== 'undefined') {
        setOwner(nextOwner);
      }
    },
    [setOwner],
  );

  const logout = useCallback(() => {
    performLogout();
    setToken(null);
    setOwner(null);
  }, [setOwner]);

  const value = useMemo<AuthContextValue>(
    () => ({
      token,
      owner,
      isAuthenticated: Boolean(token),
      setSession,
      setOwner,
      logout,
    }),
    [logout, owner, setOwner, setSession, token],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
