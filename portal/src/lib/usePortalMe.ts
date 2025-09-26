import { useQuery } from '@tanstack/react-query';

import { fetchPortalMe } from './portal';

export const PORTAL_ME_QUERY_KEY = ['portal-me'];

export const usePortalMe = () => {
  return useQuery({
    queryKey: PORTAL_ME_QUERY_KEY,
    queryFn: fetchPortalMe,
  });
};
