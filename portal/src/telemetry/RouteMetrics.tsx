import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

import { markRouteChange } from './rum';

export default function RouteMetrics() {
  const location = useLocation();

  useEffect(() => {
    markRouteChange(location.pathname, location.search);
  }, [location.pathname, location.search]);

  return null;
}
