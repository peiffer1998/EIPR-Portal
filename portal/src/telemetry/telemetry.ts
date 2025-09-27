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
const MAX_BATCH = 50;
const DEFAULT_API_PREFIX = '/api/v1';

export function emit(event: EventBase) {
  try {
    BUFFER.push(event);
    if (BUFFER.length > MAX_EVENTS) BUFFER.shift();
  } catch (error) {
    console.warn('emit telemetry failed', error);
  }
}

export function getBuffer(): EventBase[] {
  return BUFFER.slice().reverse();
}

function requeue(events: EventBase[]) {
  if (!events.length) return;
  BUFFER.unshift(...events);
  if (BUFFER.length > MAX_EVENTS) {
    BUFFER.length = MAX_EVENTS;
  }
}

function trimTrailingSlash(value: string): string {
  return value.endsWith('/') ? value.slice(0, -1) : value;
}

function normalizePath(path: string): string {
  if (!path) return '/telemetry';
  return path.startsWith('/') ? path : `/${path}`;
}

function resolveUrl(baseURL: string | undefined, path: string): string {
  const normalizedPath = normalizePath(path);
  const defaultBase = typeof api.defaults.baseURL === 'string' ? api.defaults.baseURL : '';
  const base = baseURL ?? defaultBase;
  if (!base) return normalizedPath;

  const sanitizedBase = trimTrailingSlash(base);
  if (!sanitizedBase) return normalizedPath;

  const loweredBase = sanitizedBase.toLowerCase();
  const loweredPath = normalizedPath.toLowerCase();

  if (loweredBase.endsWith('/api/v1') && loweredPath.startsWith('/api/v1/')) {
    const trimmedPath = normalizedPath.replace(/^\/api\/v1/i, '');
    const ensuredPath = trimmedPath.startsWith('/') ? trimmedPath : `/${trimmedPath}`;
    return `${sanitizedBase}${ensuredPath}`;
  }

  return `${sanitizedBase}${normalizedPath}`;
}

function extractBasePath(base: unknown): string {
  if (typeof base !== 'string' || !base) return '';
  try {
    const url = new URL(base);
    return trimTrailingSlash(url.pathname) || '';
  } catch {
    const trimmed = base.trim();
    if (!trimmed) return '';
    if (trimmed.startsWith('/')) return trimTrailingSlash(trimmed);
    if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
      try {
        const url = new URL(trimmed);
        return trimTrailingSlash(url.pathname) || '';
      } catch {
        return '';
      }
    }
    return trimTrailingSlash(`/${trimmed}`);
  }
}

function apiRoot(): string | null {
  const base = typeof api.defaults.baseURL === 'string' ? api.defaults.baseURL : '';
  if (!base) return null;
  const sanitized = trimTrailingSlash(base);
  const root = sanitized.replace(/\/(api|api\/v1)$/i, '');
  return root || null;
}

async function postBatch(path: string, payload: { events: EventBase[] }, baseURL?: string) {
  const url = resolveUrl(baseURL, path);
  await api.request({ method: 'POST', url, data: payload, baseURL: undefined });
}

export async function flush(): Promise<void> {
  if (!BUFFER.length) return;
  const count = Math.min(MAX_BATCH, BUFFER.length);
  const events = BUFFER.splice(0, count);
  const payload = { events };

  const attempts: Array<{ baseURL?: string; path: string }> = [
    { baseURL: undefined, path: '/telemetry' },
  ];

  const root = apiRoot();
  const basePath = extractBasePath(api.defaults.baseURL);
  const pathOptions = new Set<string>();
  if (basePath) pathOptions.add(basePath);
  pathOptions.add(DEFAULT_API_PREFIX);
  pathOptions.add('');

  if (root) {
    const normalizedRoot = trimTrailingSlash(root);
    for (const option of pathOptions) {
      const base = option ? `${normalizedRoot}${option}` : normalizedRoot;
      if (base) {
        attempts.push({ baseURL: base, path: '/telemetry' });
      }
    }
  }

  const attemptedUrls = new Set<string>();
  let attemptedAny = false;

  for (const attempt of attempts) {
    const targetUrl = resolveUrl(attempt.baseURL, attempt.path);
    if (attemptedUrls.has(targetUrl)) continue;
    attemptedUrls.add(targetUrl);
    attemptedAny = true;

    try {
      await postBatch(attempt.path, payload, attempt.baseURL);
      return;
    } catch (error) {
      const status = (error as AxiosError | undefined)?.response?.status ?? 0;
      if (status === 404) {
        continue;
      }
      requeue(events);
      console.warn('flush telemetry failed', error);
      return;
    }
  }

  if (!attemptedAny) {
    requeue(events);
  }
}

let debugOpen = false;
export function toggleDebugPanel(): void {
  debugOpen = !debugOpen;
  const el = document.getElementById('eipr-debug');
  if (!el) return;
  el.style.display = debugOpen ? 'block' : 'none';
}
