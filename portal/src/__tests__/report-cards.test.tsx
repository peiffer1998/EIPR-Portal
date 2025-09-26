import { screen } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';

import ReportCards from '../routes/ReportCards';
import ReportCardDetail from '../routes/ReportCardDetail';
import { renderWithProviders } from '../test-utils';

const sampleReportCards = vi.hoisted(() => ([
  {
    id: 'card-1',
    account_id: 'acct-1',
    owner_id: 'owner-1',
    pet_id: 'pet-1',
    occurred_on: '2025-01-02',
    title: 'Play day',
    summary: 'Rex enjoyed playgroup and a meal.',
    rating: 5,
    status: 'sent',
    pet_name: 'Rex',
    owner_name: 'Jamie Portal',
    media: [
      {
        id: 'media-1',
        position: 0,
        display_url: 'https://example.com/photo.jpg',
        document: {
          id: 'doc-1',
          file_name: 'photo.jpg',
          url: 'https://example.com/photo.jpg',
          url_web: null,
          content_type: 'image/jpeg',
          created_at: '2025-01-02T12:00:00Z',
        },
      },
    ],
    friends: [
      { id: 'friend-1', name: 'Milo', pet_type: 'dog' },
    ],
    created_at: '2025-01-02T12:00:00Z',
    updated_at: '2025-01-02T12:05:00Z',
  },
]));

vi.mock('../lib/usePortalMe', () => ({
  usePortalMe: () => ({
    data: {
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
        { id: 'pet-1', name: 'Rex', pet_type: 'dog', immunization_records: [] },
      ],
    },
    isLoading: false,
  }),
}));

vi.mock('../lib/portal', () => ({
  fetchReportCards: vi.fn().mockResolvedValue(sampleReportCards),
  fetchReportCardDetail: vi.fn().mockResolvedValue(sampleReportCards[0]),
}));

describe('ReportCards route', () => {
  it('lists report cards with links', async () => {
    renderWithProviders(<ReportCards />, { route: '/report-cards' });
    expect(await screen.findByText('Play day')).toBeInTheDocument();
    expect(screen.getByText('Rex')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /view details/i })).toBeInTheDocument();
  });
});

describe('ReportCardDetail route', () => {
  it('renders report card details', async () => {
    renderWithProviders(
      (
        <Routes>
          <Route path="/report-cards/:cardId" element={<ReportCardDetail />} />
        </Routes>
      ),
      { route: '/report-cards/card-1' },
    );
    expect(await screen.findByText(/play day/i)).toBeInTheDocument();
    expect(screen.getByText(/Overall rating/i)).toBeInTheDocument();
    expect(screen.getByText(/Milo/)).toBeInTheDocument();
  });
});
