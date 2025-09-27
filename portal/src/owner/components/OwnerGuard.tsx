import { Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';

import Loading from '../../ui/Loading';
import Page from '../../ui/Page';
import { Card, CardHeader } from '../../ui/Card';
import Button from '../../ui/Button';
import { useAuth } from '../../state/useAuth';
import { fetchMe, toStoredOwner } from '../lib/fetchers';

const OWNER_ME_QUERY_KEY = ['owner', 'me'];

const OwnerGuard = ({ children }: { children: JSX.Element }): JSX.Element => {
  const { isAuthenticated, setOwner, logout } = useAuth();

  const meQuery = useQuery({
    queryKey: OWNER_ME_QUERY_KEY,
    queryFn: fetchMe,
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });

  useEffect(() => {
    if (meQuery.data?.id) {
      setOwner(toStoredOwner(meQuery.data));
    }
  }, [meQuery.data, setOwner]);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (meQuery.isLoading) {
    return <Loading text="Loading your account…" />;
  }

  if (meQuery.isError || !meQuery.data?.id) {
    return (
      <div className="mx-auto max-w-2xl py-10">
        <Page>
          <Card>
            <CardHeader title="Authentication expired" sub="Please sign in again to continue." />
            <Button
              variant="primary"
              className="w-full mt-2"
              onClick={() => {
                logout();
              }}
            >
              Return to login
            </Button>
          </Card>
        </Page>
      </div>
    );
  }

  return children;
};

export default OwnerGuard;
