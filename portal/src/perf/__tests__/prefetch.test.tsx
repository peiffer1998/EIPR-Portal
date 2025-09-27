import { describe, expect, it, vi } from 'vitest';
import { prefetchModule } from '../prefetch';

describe('prefetchModule', () => {
  it('invokes importer once', () => {
    const importer = vi.fn(() => Promise.resolve());
    const trigger = prefetchModule(importer);
    trigger();
    trigger();
    expect(importer).toHaveBeenCalledTimes(1);
  });
});
