import type { AxiosError } from 'axios';

import api from '../lib/api';

type EventBase = {
  ts: number;
  type: string;
  requestId?: string;
  message?: string;
  meta?: unknown;
};

const BUFFER: EventBase[] = [];
const MAX_EVENTS = 200;

export function emit(event: EventBase) {
  try {
    BUFFER.push(event);
    if (BUFFER.length > MAX_EVENTS) BUFFER.shift();
  } catch (error) {
    console.warn("emit telemetry failed", error);
  }
}

export function getBuffer(): EventBase[] {
  return BUFFER.slice().reverse();
}

export async function flush(): Promise<void> {
  if (!BUFFER.length) return;
  const payload = { events: BUFFER.slice(-50) };

  const tryFallback = async () => {
    const base = api.defaults.baseURL ?? '';
    const root = base.replace(/\/$/, '').replace(/\/(api|api\/v1)$/i, '');
    if (!root) return;
    await api.post('/api/v1/telemetry', payload, { baseURL: root });
  };

  try {
    await api.post('/telemetry', payload);
  } catch (error) {
    const axiosError = error as AxiosError | undefined;
    const status = axiosError?.response?.status;
    if (status === 404) {
      try {
        await tryFallback();
      } catch {
        /* swallow missing telemetry endpoint */
      }
      return;
    }

    try {
      await tryFallback();
    } catch (fallbackError) {
      console.warn('flush telemetry failed', fallbackError);
    }
  }
}

let debugOpen = false;
export function toggleDebugPanel(): void {
  debugOpen = !debugOpen;
  const el = document.getElementById("eipr-debug");
  if (!el) return;
  el.style.display = debugOpen ? "block" : "none";
}
