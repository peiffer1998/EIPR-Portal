import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import PrintLayout from "../../../print/PrintLayout";
import SimpleQR from "../../../print/SimpleQR";
import { getAppointment } from "../../lib/groomingFetchers";

export default function GroomTicket() {
  const { appointmentId = "" } = useParams();

  const { data } = useQuery({
    queryKey: ["groom-ticket", appointmentId],
    queryFn: () => getAppointment(appointmentId),
    enabled: Boolean(appointmentId),
  });

  const appointment: any = data ?? {};
  const meta = [
    { label: "Appointment", value: appointmentId },
    { label: "Start", value: appointment?.start_at ?? "" },
    { label: "Specialist", value: appointment?.specialist?.name ?? appointment?.specialist_name ?? appointment?.specialist_id },
  ];

  const rows = [
    { label: "Pet", value: appointment?.pet?.name ?? appointment?.pet_id ?? "" },
    { label: "Owner", value: [appointment?.owner?.first_name, appointment?.owner?.last_name].filter(Boolean).join(" ") },
    { label: "Service", value: appointment?.service?.name ?? appointment?.service_id ?? "" },
    { label: "Duration", value: appointment?.duration_minutes ? `${appointment.duration_minutes} minutes` : "" },
    { label: "Add-ons", value: (appointment?.addons || []).map((addon: any) => addon.name ?? addon).join(", ") },
  ].filter((row) => row.value);

  const instructions = appointment?.instructions ?? appointment?.notes ?? "";

  return (
    <PrintLayout title="Grooming Ticket" meta={meta}>
      <section className="print-block" aria-labelledby="groom-ticket-summary">
        <div className="print-section-title" id="groom-ticket-summary">Appointment Summary</div>
        <table className="print-table">
          <tbody>
            {rows.map((row) => (
              <tr key={row.label}>
                <th scope="row" style={{ width: "28%" }}>{row.label}</th>
                <td>{row.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="print-block" aria-labelledby="groom-ticket-code">
        <div className="print-section-title" id="groom-ticket-code">Check In Code</div>
        <SimpleQR value={appointmentId} />
      </section>

      <section className="print-block" aria-labelledby="groom-ticket-notes">
        <div className="print-section-title" id="groom-ticket-notes">Styling Notes</div>
        <div className="print-notes" role="textbox" aria-label="Styling notes">
          {instructions || "(none provided)"}
        </div>
      </section>

      <section className="print-block" aria-labelledby="groom-ticket-checklist">
        <div className="print-section-title" id="groom-ticket-checklist">Checklist</div>
        <table className="print-table">
          <tbody>
            {["Bath", "Dry", "Nails", "Ears", "Teeth", "Brush", "Extras"].map((item) => (
              <tr key={item}>
                <td>{item}</td>
                <td style={{ width: "30%" }}>_______</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </PrintLayout>
  );
}
