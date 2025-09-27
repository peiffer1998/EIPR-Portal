import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { PropsWithChildren } from "react";

import api from "../../lib/api";
import { getMe, loginWithPassword, type Me } from "../lib/staffApi";

const KEY = "eipr.staff.token";

type Ctx = {
  token: string | null;
  user: Me | null;
  isAuthed: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  refreshMe: () => Promise<void>;
};

const StaffAuthContext = createContext<Ctx | null>(null);

const readStoredToken = () => {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(KEY);
  } catch {
    return null;
  }
};

const saveToken = (token: string | null) => {
  if (typeof window === "undefined") return;
  if (token) {
    window.localStorage.setItem(KEY, token);
  } else {
    window.localStorage.removeItem(KEY);
  }
};

export function StaffAuthProvider({ children }: PropsWithChildren) {
  const [token, setToken] = useState<string | null>(() => readStoredToken());
  const [user, setUser] = useState<Me | null>(null);

  useEffect(() => {
    if (!token) return;
    api.defaults.headers.common = api.defaults.headers.common ?? {};
    api.defaults.headers.common.Authorization = `Bearer ${token}`;
    getMe().then(setUser).catch(() => {});
  }, [token]);

  const login = async (email: string, password: string) => {
    const next = await loginWithPassword(email, password);
    setToken(next);
    saveToken(next);
    api.defaults.headers.common = api.defaults.headers.common ?? {};
    api.defaults.headers.common.Authorization = `Bearer ${next}`;
    setUser(await getMe());
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    saveToken(null);
    if (api.defaults.headers.common) {
      delete api.defaults.headers.common.Authorization;
    }
  };

  const refreshMe = async () => {
    setUser(await getMe());
  };

  const value = useMemo(
    () => ({ token, user, isAuthed: Boolean(token), login, logout, refreshMe }),
    [token, user],
  );

  return <StaffAuthContext.Provider value={value}>{children}</StaffAuthContext.Provider>;
}

export const useStaffAuth = () => {
  const ctx = useContext(StaffAuthContext);
  if (!ctx) throw new Error("useStaffAuth outside provider");
  return ctx;
};
