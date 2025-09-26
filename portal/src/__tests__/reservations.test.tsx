import { screen } from '@testing-library/react';
import { vi } from 'vitest';

import Reservations from '../routes/Reservations';
import { renderWithProviders } from '../test-utils';

const sampleData = {
  owner: {
    id: 'owner-1',
    preferred_contact_method: null,
    user: {
      first_name: 'Jamie',
      last_name: 'Portal',
      email: 'jamie@example.com',
    },
  },
  pets: [
    {
      id: 'pet-1',
      name: 'Rex',
      pet_type: 'dog',
      immunization_records: [],
    },
  ],
  upcoming_reservations: [
    {
      id: 'res-1',
      reservation_type: 'boarding',
      status: 'confirmed',
      start_at: new Date().toISOString(),
      end_at: new Date(Date.now() + 86_400_000).toISOString(),
      notes: 'Bring favourite toy',
      pet: {
        id: 'pet-1',
        name: 'Rex',
        pet_type: 'dog',
        immunization_records: [],
      },
    },
  ],
  past_reservations: [],
  unpaid_invoices: [],
  recent_paid_invoices: [],
  documents: [],
};

vi.mock('../lib/usePortalMe', () => ({
  usePortalMe: () => ({ data: sampleData, isLoading: false }),
  PORTAL_ME_QUERY_KEY: ['portal-me'],
}));

vi.mock('../lib/portal', () => ({
  requestReservation: vi.fn().mockResolvedValue({}),
  cancelReservation: vi.fn().mockResolvedValue({}),
}));

describe('Reservations', () => {
  it('renders upcoming reservations', () => {
    renderWithProviders(<Reservations />, { route: '/' });
    expect(screen.getByText('Upcoming')).toBeInTheDocument();
    expect(screen.getAllByText('Rex')[0]).toBeInTheDocument();
    expect(screen.getByText(/confirmed/i)).toBeInTheDocument();
  });
});
