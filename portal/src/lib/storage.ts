export const TOKEN_STORAGE_KEY = 'eipr.portal.token';
export const OWNER_STORAGE_KEY = 'eipr.portal.owner';

export interface StoredOwnerSummary {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
}

export const readToken = (): string | null => {
  return typeof localStorage === 'undefined' ? null : localStorage.getItem(TOKEN_STORAGE_KEY);
};

export const writeToken = (token: string | null): void => {
  if (typeof localStorage === 'undefined') return;
  if (token) {
    localStorage.setItem(TOKEN_STORAGE_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_STORAGE_KEY);
  }
};

export const readOwner = (): StoredOwnerSummary | null => {
  if (typeof localStorage === 'undefined') return null;
  const raw = localStorage.getItem(OWNER_STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredOwnerSummary;
  } catch {
    localStorage.removeItem(OWNER_STORAGE_KEY);
    return null;
  }
};

export const writeOwner = (owner: StoredOwnerSummary | null): void => {
  if (typeof localStorage === 'undefined') return;
  if (owner) {
    localStorage.setItem(OWNER_STORAGE_KEY, JSON.stringify(owner));
  } else {
    localStorage.removeItem(OWNER_STORAGE_KEY);
  }
};
