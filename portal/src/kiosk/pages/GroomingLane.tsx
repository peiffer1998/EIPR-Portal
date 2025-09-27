import { useMemo, useState } from 'react';

import ScanBox from '../components/ScanBox';
import { getAppointment, setAppointmentStatus, type GroomingStatus } from '../lib/fetchers';

type Appointment = Record<string, any> & {
  id: string;
  pet?: { name?: string } | null;
  pet_id?: string;
  service?: { name?: string } | null;
  service_id?: string;
};

const STATUS_OPTIONS: GroomingStatus[] = ['ARRIVED', 'IN_PROGRESS', 'COMPLETE', 'PICKED_UP'];

const STATUS_CLASSES: Record<GroomingStatus, string> = {
  ARRIVED: 'bg-slate-900 hover:bg-slate-800',
  IN_PROGRESS: 'bg-blue-600 hover:bg-blue-700',
  COMPLETE: 'bg-purple-700 hover:bg-purple-800',
  PICKED_UP: 'bg-green-600 hover:bg-green-700',
};

export default function GroomingLane() {
  const [appointment, setAppointment] = useState<Appointment | null>(null);
  const [loading, setLoading] = useState(false);

  const appointmentName = useMemo(() => {
    if (!appointment) return '';
    const petName = appointment.pet?.name ?? appointment.pet_id ?? 'Guest';
    const serviceName = appointment.service?.name ?? appointment.service_id ?? 'Grooming';
    return `${petName} • ${serviceName}`;
  }, [appointment]);

  const loadAppointment = async (id: string) => {
    setLoading(true);
    try {
      const result = await getAppointment(id);
      setAppointment(result as Appointment);
    } catch {
      window.alert('Unable to load appointment');
      setAppointment(null);
    } finally {
      setLoading(false);
    }
  };

  const updateStatus = async (status: GroomingStatus) => {
    if (!appointment) return;
    setLoading(true);
    try {
      await setAppointmentStatus(appointment.id, status);
      window.alert(`${status.replace('_', ' ')} status set`);
    } catch {
      window.alert('Unable to update status');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid gap-3">
      <ScanBox label="Scan or type grooming appointment ID" onSubmit={loadAppointment} />
      {loading ? <div className="text-slate-600">Working…</div> : null}
      {appointment ? (
        <div className="grid gap-2">
          <div className="text-2xl font-semibold">{appointmentName}</div>
          <div className="flex gap-2 flex-wrap">
            {STATUS_OPTIONS.map((status) => (
              <button
                key={status}
                type="button"
                className={`px-4 py-3 rounded text-lg text-white ${STATUS_CLASSES[status]}`}
                onClick={() => updateStatus(status)}
                disabled={loading}
              >
                {status.replace('_', ' ')}
              </button>
            ))}
            <a
              className="px-4 py-3 rounded border text-lg"
              href={`/staff/print/groom-ticket/${appointment.id}`}
              target="_blank"
              rel="noreferrer"
            >
              Print Ticket
            </a>
          </div>
        </div>
      ) : null}
    </div>
  );
}
