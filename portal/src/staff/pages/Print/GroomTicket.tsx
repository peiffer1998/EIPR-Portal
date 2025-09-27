import { useEffect } from "react";
import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getAppointment } from "../../lib/groomingFetchers";

export default function GroomTicket() {
  const { appointmentId = "" } = useParams();

  const { data } = useQuery({
    queryKey: ["groom-ticket", appointmentId],
    queryFn: () => getAppointment(appointmentId),
    enabled: Boolean(appointmentId),
  });

  useEffect(() => {
    if (appointmentId) {
      const handle = setTimeout(() => window.print(), 100);
      return () => clearTimeout(handle);
    }
    return undefined;
  }, [appointmentId, data]);

  const appointment: any = data || {};
  const pet = appointment.pet || { name: appointment.pet_name, id: appointment.pet_id };
  const owner = appointment.owner || {
    first_name: appointment.owner_first_name,
    last_name: appointment.owner_last_name,
  };
  const specialist = appointment.specialist || {
    name: appointment.specialist_name,
    id: appointment.specialist_id,
  };
  const service = appointment.service || {
    name: appointment.service_name,
  };

  return (
    <div style={{ fontFamily: "ui-sans-serif", padding: "28px", lineHeight: 1.45 }}>
      <header style={{ marginBottom: "18px" }}>
        <h1 style={{ fontSize: "26px", margin: 0 }}>Grooming Ticket</h1>
        <div style={{ color: "#475569", marginTop: "4px" }}>Appointment #{appointmentId}</div>
      </header>

      <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
        <div>
          <h2 style={{ fontSize: "14px", fontWeight: 600, textTransform: "uppercase", color: "#64748b" }}>Pet</h2>
          <p style={{ margin: "4px 0 0" }}><strong>{pet?.name || pet?.id || "Unknown"}</strong></p>
          <p style={{ margin: 0, color: "#475569" }}>ID: {pet?.id || "—"}</p>
        </div>
        <div>
          <h2 style={{ fontSize: "14px", fontWeight: 600, textTransform: "uppercase", color: "#64748b" }}>Owner</h2>
          <p style={{ margin: "4px 0 0" }}>
            <strong>
              {(owner?.first_name || "") + (owner?.last_name ? ` ${owner.last_name}` : "") || "Unknown"}
            </strong>
          </p>
          <p style={{ margin: 0, color: "#475569" }}>ID: {owner?.id || "—"}</p>
        </div>
        <div>
          <h2 style={{ fontSize: "14px", fontWeight: 600, textTransform: "uppercase", color: "#64748b" }}>Specialist</h2>
          <p style={{ margin: "4px 0 0" }}><strong>{specialist?.name || specialist?.id || "Unassigned"}</strong></p>
          <p style={{ margin: 0, color: "#475569" }}>ID: {specialist?.id || "—"}</p>
        </div>
        <div>
          <h2 style={{ fontSize: "14px", fontWeight: 600, textTransform: "uppercase", color: "#64748b" }}>Service</h2>
          <p style={{ margin: "4px 0 0" }}><strong>{service?.name || appointment.service_id || "—"}</strong></p>
          <p style={{ margin: 0, color: "#475569" }}>Service ID: {appointment.service_id || "—"}</p>
        </div>
      </section>

      <section style={{ marginTop: "22px", display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
        <div>
          <h2 style={{ fontSize: "14px", fontWeight: 600, textTransform: "uppercase", color: "#64748b" }}>Timing</h2>
          <p style={{ margin: "4px 0 0", color: "#475569" }}>Start: {appointment.start_at || "—"}</p>
          <p style={{ margin: "2px 0 0", color: "#475569" }}>End: {appointment.end_at || "—"}</p>
          <p style={{ margin: "2px 0 0", color: "#475569" }}>Duration: {appointment.duration_min || "—"} min</p>
          <p style={{ margin: "2px 0 0", color: "#475569" }}>Status: {appointment.status || "—"}</p>
        </div>
        <div>
          <h2 style={{ fontSize: "14px", fontWeight: 600, textTransform: "uppercase", color: "#64748b" }}>Financial</h2>
          <p style={{ margin: "4px 0 0", color: "#475569" }}>
            Commission: {appointment.commission_amount != null ? `$${appointment.commission_amount}` : "—"}
          </p>
          <p style={{ margin: "2px 0 0", color: "#475569" }}>
            Commission Rate: {appointment.commission_rate != null ? `${appointment.commission_rate}%` : "—"}
          </p>
          <p style={{ margin: "2px 0 0", color: "#475569" }}>Base Amount: {appointment.basis_amount ?? "—"}</p>
        </div>
        <div>
          <h2 style={{ fontSize: "14px", fontWeight: 600, textTransform: "uppercase", color: "#64748b" }}>Add-ons</h2>
          <p style={{ margin: "4px 0 0", color: "#475569" }}>
            {(appointment.addon_names && appointment.addon_names.length)
              ? appointment.addon_names.join(", ")
              : "None"}
          </p>
        </div>
      </section>

      <section style={{ marginTop: "22px" }}>
        <h2 style={{ fontSize: "14px", fontWeight: 600, textTransform: "uppercase", color: "#64748b" }}>Notes</h2>
        <p style={{ margin: "6px 0 0", color: "#334155", whiteSpace: "pre-wrap" }}>
          {appointment.notes || "No additional notes."}
        </p>
      </section>
    </div>
  );
}
