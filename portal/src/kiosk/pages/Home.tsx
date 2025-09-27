import { useNavigate } from 'react-router-dom';

import BigButton from '../components/BigButton';

export default function KioskHome() {
  const navigate = useNavigate();
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      <BigButton label="Boarding — Check-In" onClick={() => navigate('/staff/kiosk/boarding/checkin')} />
      <BigButton label="Boarding — Check-Out" onClick={() => navigate('/staff/kiosk/boarding/checkout')} />
      <BigButton label="Daycare — Check-In Today" onClick={() => navigate('/staff/kiosk/daycare/checkin')} />
      <BigButton label="Daycare — Check-Out Today" onClick={() => navigate('/staff/kiosk/daycare/checkout')} />
      <BigButton label="Grooming — Status & Ticket" onClick={() => navigate('/staff/kiosk/grooming')} />
      <BigButton label="Quick Print" onClick={() => navigate('/staff/kiosk/print')} variant="ghost" />
    </div>
  );
}
