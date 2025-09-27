import { getBuffer } from './telemetry';

type VitalBuckets = {
  LCP: number[];
  CLS: number[];
  INP: number[];
  FCP: number[];
  TTFB: number[];
};

type HttpAggregation = {
  ms: number[];
  codes: Record<string, number>;
};

export type Aggregation = {
  vitals: VitalBuckets;
  http: HttpAggregation;
  errors: number;
  windowMs: number;
};

const defaultVitals = (): VitalBuckets => ({
  LCP: [],
  CLS: [],
  INP: [],
  FCP: [],
  TTFB: [],
});

export function aggregate(windowMs = 10 * 60 * 1000): Aggregation {
  const now = Date.now();
  const events = getBuffer().filter((event) => now - event.ts <= windowMs);

  const vitals = defaultVitals();
  const http: HttpAggregation = { ms: [], codes: {} };
  let errors = 0;

  for (const event of events) {
    if (event.type.startsWith('vital.')) {
      const [, name] = event.type.split('.', 2);
      const bucket = (vitals as Record<string, number[]>)[name];
      const value = Number((event.meta as any)?.value ?? event.message ?? 0);
      if (bucket && Number.isFinite(value)) {
        bucket.push(value);
      }
    } else if (event.type === 'http.timing') {
      const duration = Number((event.meta as any)?.ms ?? 0);
      if (Number.isFinite(duration) && duration > 0) {
        http.ms.push(duration);
      }
      const code = String((event.meta as any)?.code ?? '');
      if (code) {
        http.codes[code] = (http.codes[code] ?? 0) + 1;
      }
    } else if (event.type === 'http.error' || event.type === 'ui.error') {
      errors += 1;
    }
  }

  return { vitals, http, errors, windowMs };
}

export function percentile(values: number[], p: number): number {
  if (!values.length) return 0;
  if (values.length === 1) return values[0];

  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(
    sorted.length - 1,
    Math.max(0, Math.ceil((p / 100) * sorted.length) - 1),
  );
  return sorted[index];
}
