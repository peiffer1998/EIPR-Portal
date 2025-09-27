import { Outlet } from 'react-router-dom';
import { useState } from 'react';

import KioskLock, { STORAGE_KEY } from './Lock';

const isStorageAvailable = () =>
  typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined';

const getInitialUnlocked = () =>
  isStorageAvailable() && window.sessionStorage.getItem(STORAGE_KEY) === '1';


export default function KioskShell() {
  const [unlocked, setUnlocked] = useState<boolean>(getInitialUnlocked);

  if (!unlocked) {
    return <KioskLock onUnlock={() => setUnlocked(true)} />;
  }

  return (
    <div className="min-h-screen bg-slate-100 grid grid-rows-[auto_1fr]">
      <header className="bg-slate-900 text-white p-4 flex items-center justify-between">
        <div className="text-2xl font-bold">Front Desk</div>
        <div className="flex gap-2">
          <a href="/staff" className="px-3 py-2 rounded bg-slate-800">
            Back to Staff
          </a>
          <button
            type="button"
            className="px-3 py-2 rounded bg-slate-800"
            onClick={() => {
              if (isStorageAvailable()) {
                window.sessionStorage.removeItem(STORAGE_KEY);
              }
              setUnlocked(false);
            }}
          >
            Lock
          </button>
        </div>
      </header>
      <main className="p-6 grid gap-4">
        <Outlet />
      </main>
    </div>
  );
}
