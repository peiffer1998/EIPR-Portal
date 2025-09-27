import { useEffect, useState } from 'react';

const STORAGE_KEY = 'kiosk_unlocked';

const isStorageAvailable = () =>
  typeof window !== 'undefined' && typeof window.sessionStorage !== 'undefined';

const getPin = () => {
  const raw = import.meta.env.VITE_KIOSK_PIN;
  return typeof raw === 'string' && raw.trim().length > 0 ? raw.trim() : '1234';
};

type KioskLockProps = {
  onUnlock: () => void;
};

export default function KioskLock({ onUnlock }: KioskLockProps) {
  const [entry, setEntry] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!isStorageAvailable()) return;
    if (window.sessionStorage.getItem(STORAGE_KEY) === '1') {
      onUnlock();
    }
  }, [onUnlock]);

  const handleUnlock = () => {
    const pin = getPin();
    if (entry.trim() === pin) {
      if (isStorageAvailable()) {
        window.sessionStorage.setItem(STORAGE_KEY, '1');
      }
      setError('');
      setEntry('');
      onUnlock();
    } else {
      setError('Incorrect PIN');
      setEntry('');
    }
  };

  return (
    <div className="min-h-screen bg-slate-900 text-white flex items-center justify-center">
      <div className="grid gap-3 w-full max-w-sm p-6">
        <div className="text-2xl font-semibold text-center">Enter PIN</div>
        <input
          type="password"
          inputMode="numeric"
          className="text-3xl text-center rounded px-3 py-2 text-slate-900"
          value={entry}
          onChange={(event) => setEntry(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') handleUnlock();
          }}
          aria-label="Kiosk PIN"
        />
        <button
          type="button"
          className="px-4 py-3 rounded bg-orange-500 text-white text-xl"
          onClick={handleUnlock}
        >
          Unlock
        </button>
        {error ? <div className="text-center text-red-300 text-sm">{error}</div> : null}
      </div>
    </div>
  );
}

export { STORAGE_KEY };
