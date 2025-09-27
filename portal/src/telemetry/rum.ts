import { emit, flush } from './telemetry';

type MetricHandler = {
  value: number;
  rating?: string;
  id?: string;
};

let webVitalsStarted = false;
export async function startWebVitals(): Promise<void> {
  if (webVitalsStarted) return;
  if (typeof window === 'undefined') return;
  webVitalsStarted = true;

  try {
    const module = await import('web-vitals');
    const handlers: Array<[string, ((callback: (metric: MetricHandler) => void) => void) | undefined]> = [
      ['CLS', (module as any).onCLS],
      ['LCP', (module as any).onLCP],
      ['INP', (module as any).onINP ?? (module as any).onFID],
      ['FCP', (module as any).onFCP],
      ['TTFB', (module as any).onTTFB],
    ];

    const createListener = (name: string) => (metric: MetricHandler) => {
      emit({
        ts: Date.now(),
        type: `vital.${name}`,
        message: String(metric.value),
        meta: {
          value: metric.value,
          rating: metric.rating,
          id: metric.id,
        },
      });
    };

    handlers.forEach(([name, cb]) => {
      try {
        cb?.(createListener(name));
      } catch (error) {
        console.warn(`web-vitals handler failed for ${name}`, error);
      }
    });
  } catch (error) {
    console.warn('web-vitals import failed', error);
  }
}

let lastNavStarted = typeof performance !== 'undefined' ? performance.now() : Date.now();
let lastPath = typeof window !== 'undefined' ? `${window.location.pathname}${window.location.search}` : '';
let routeInitialised = false;

export function markRouteChange(pathname?: string, search?: string): void {
  if (typeof performance === 'undefined') return;

  const now = performance.now();
  const nextPath = pathname !== undefined || search !== undefined
    ? `${pathname ?? ''}${search ?? ''}`
    : typeof window !== 'undefined'
      ? `${window.location.pathname}${window.location.search}`
      : lastPath;

  if (routeInitialised) {
    const duration = Math.max(0, Math.round(now - lastNavStarted));
    emit({
      ts: Date.now(),
      type: 'spa.nav',
      message: lastPath,
      meta: {
        from: lastPath,
        to: nextPath,
        ms: duration,
      },
    });
  }

  emit({
    ts: Date.now(),
    type: 'spa.view',
    message: nextPath,
    meta: {
      path: nextPath,
    },
  });

  lastPath = nextPath;
  lastNavStarted = now;
  routeInitialised = true;
}

let flushInterval: ReturnType<typeof setInterval> | null = null;
export function startFlushLoop(): void {
  if (flushInterval) return;
  if (typeof window === 'undefined') return;

  flushInterval = setInterval(() => {
    void flush().catch(() => undefined);
  }, 15_000);

  void flush().catch(() => undefined);
}
