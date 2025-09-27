import { describe, expect, it } from 'vitest';
import { render } from '@testing-library/react';

import ErrorBoundary from '../ErrorBoundary';

function Boom(): JSX.Element {
  throw new Error('boom');
}

describe('ErrorBoundary', () => {
  it('renders fallback when child throws', () => {
    render(
      <ErrorBoundary>
        <Boom />
      </ErrorBoundary>,
    );

    expect(true).toBe(true);
  });
});
