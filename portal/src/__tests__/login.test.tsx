import { fireEvent, screen } from '@testing-library/react';
import { vi } from 'vitest';

import LoginRegister from '../routes/LoginRegister';
import { renderWithProviders } from '../test-utils';

vi.mock('../lib/portal', () => ({
  fetchPortalMe: vi.fn().mockResolvedValue({
    owner: {
      id: 'owner-1',
      preferred_contact_method: null,
      user: {
        first_name: 'Jamie',
        last_name: 'Portal',
        email: 'jamie@example.com',
      },
    },
    pets: [],
    upcoming_reservations: [],
    past_reservations: [],
    unpaid_invoices: [],
    recent_paid_invoices: [],
    documents: [],
  }),
}));

vi.mock('../lib/auth', () => ({
  login: vi.fn().mockResolvedValue('token-123'),
  registerOwner: vi.fn().mockResolvedValue({
    token: 'token-456',
    owner: {
      id: 'owner-1',
      firstName: 'Jamie',
      lastName: 'Portal',
      email: 'jamie@example.com',
    },
  }),
  getMe: vi.fn(),
}));

describe('LoginRegister', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('toggles between login and registration forms', () => {
    renderWithProviders(<LoginRegister />, { route: '/login' });

    expect(screen.getByText('Sign In')).toBeInTheDocument();
    const registerTab = screen.getByRole('button', { name: 'Register' });
    fireEvent.click(registerTab);
    expect(screen.getByText('Create account')).toBeInTheDocument();

    const loginTab = screen.getByRole('button', { name: 'Login' });
    fireEvent.click(loginTab);
    expect(screen.getByText('Sign In')).toBeInTheDocument();
  });
});
