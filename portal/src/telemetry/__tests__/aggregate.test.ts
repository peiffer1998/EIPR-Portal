import { describe, expect, it } from 'vitest';

import { aggregate, percentile } from '../aggregate';
import { emit } from '../telemetry';

describe('telemetry aggregate', () => {
  it('returns vitals, http, and error counts', () => {
    const result = aggregate(600_000);
    expect(result).toHaveProperty('vitals');
    expect(result).toHaveProperty('http');
    expect(result).toHaveProperty('errors');
  });

  it('computes percentiles with sample data', () => {
    emit({ ts: Date.now(), type: 'vital.LCP', meta: { value: 1000 } });
    emit({ ts: Date.now(), type: 'vital.LCP', meta: { value: 2000 } });
    const values = [1, 2, 3, 4, 5];
    expect(percentile(values, 50)).toBe(3);
    expect(percentile(values, 95)).toBe(5);
  });
});
