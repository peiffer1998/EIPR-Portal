import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import type { PropsWithChildren } from 'react';

import './staff-toast.css';

type ToastLevel = 'info' | 'success' | 'error';

interface ToastEntry {
  id: number;
  message: string;
  level: ToastLevel;
}

interface StaffToastContextValue {
  showToast: (message: string, level?: ToastLevel, durationMs?: number) => void;
}

const StaffToastContext = createContext<StaffToastContextValue | undefined>(undefined);

export const StaffToastProvider = ({ children }: PropsWithChildren) => {
  const [toasts, setToasts] = useState<ToastEntry[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((current) => current.filter((toast) => toast.id !== id));
  }, []);

  const showToast = useCallback(
    (message: string, level: ToastLevel = 'info', durationMs = 4000) => {
      const id = Date.now() + Math.floor(Math.random() * 1000);
      setToasts((current) => [...current, { id, message, level }]);
      if (durationMs > 0) {
        window.setTimeout(() => dismiss(id), durationMs);
      }
    },
    [dismiss],
  );

  const value = useMemo<StaffToastContextValue>(() => ({ showToast }), [showToast]);

  return (
    <StaffToastContext.Provider value={value}>
      {children}
      <div className="staff-toast-container">
        {toasts.map((toast) => (
          <button
            key={toast.id}
            type="button"
            className={`staff-toast staff-toast-${toast.level}`}
            onClick={() => dismiss(toast.id)}
          >
            {toast.message}
          </button>
        ))}
      </div>
    </StaffToastContext.Provider>
  );
};

export const useStaffToast = (): StaffToastContextValue => {
  const ctx = useContext(StaffToastContext);
  if (!ctx) {
    throw new Error('useStaffToast must be used within StaffToastProvider');
  }
  return ctx;
};
