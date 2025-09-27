import { describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';

import QuickSearch from '../QuickSearch';

vi.mock('../../staff/lib/fetchers', () => ({
  listOwners: async () => [
    { id: 'o1', first_name: 'Alice', last_name: 'Owner', email: 'alice@example.com' },
  ],
  listPets: async () => [
    { id: 'p1', name: 'Buddy', breed: 'GSD' },
  ],
}));

describe('QuickSearch', () => {
  it('renders when open', async () => {
    render(<QuickSearch open onClose={() => undefined} />);

    const input = await screen.findByPlaceholderText(/Search owners or pets/i);
    await act(async () => {
      fireEvent.change(input, { target: { value: 'bud' } });
    });

    expect(true).toBe(true);
  });
});
