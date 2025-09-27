import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import PrintLayout from "../../../print/PrintLayout";
import SimpleQR from "../../../print/SimpleQR";
import { getReservation } from "../../lib/reservationOps";

export default function PrintRunCard() {
  const { reservationId = "" } = useParams();

  const { data } = useQuery({
    queryKey: ["reservation-print", reservationId],
    queryFn: () => getReservation(reservationId),
    enabled: Boolean(reservationId),
  });

  const reservation = data ?? {};
  const meta = [
    { label: "Reservation", value: reservationId },
    { label: "Run", value: reservation?.run?.name ?? reservation?.run_id ?? "Unassigned" },
  ];

  const weight = reservation?.pet?.weight;
  const weightUnit = reservation?.pet?.weight_unit ?? "lbs";
  const summaryRows = [
    { label: "Pet", value: reservation?.pet?.name ?? reservation?.pet_id },
    { label: "Owner", value: [reservation?.owner?.first_name, reservation?.owner?.last_name].filter(Boolean).join(" ") || "" },
    { label: "Breed", value: reservation?.pet?.breed ?? "" },
    {
      label: "Dates",
      value:
        reservation?.start_at && reservation?.end_at
          ? `${reservation.start_at} → ${reservation.end_at}`
          : reservation?.start_at ?? "",
    },
    { label: "Weight", value: weight ? `${weight} ${weightUnit}` : "" },
  ].filter((row) => row.value);

  const feeding = reservation?.feeding_instructions ?? reservation?.feeding ?? "";
  const medications = reservation?.medications ?? reservation?.medication_instructions ?? "";
  const notes = reservation?.notes ?? reservation?.special_requests ?? "";

  return (
    <PrintLayout title="Run Card" meta={meta}>
      <section className="print-block" aria-labelledby="run-card-summary">
        <div className="print-section-title" id="run-card-summary">Summary</div>
        <table className="print-table">
          <tbody>
            {summaryRows.map((row) => (
              <tr key={row.label}>
                <th scope="row" style={{ width: "30%" }}>{row.label}</th>
                <td>{row.value}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="print-block" aria-labelledby="run-card-qr">
        <div className="print-section-title" id="run-card-qr">Check In Code</div>
        <SimpleQR value={reservationId} />
      </section>

      <section className="print-block" aria-labelledby="run-card-feeding">
        <div className="print-section-title" id="run-card-feeding">Feeding Instructions</div>
        <div className="print-notes" role="textbox" aria-label="Feeding instructions">
          {feeding || "(none provided)"}
        </div>
      </section>

      <section className="print-block" aria-labelledby="run-card-meds">
        <div className="print-section-title" id="run-card-meds">Medication Notes</div>
        <div className="print-notes" role="textbox" aria-label="Medication notes">
          {medications || "(none provided)"}
        </div>
      </section>

      <section className="print-block" aria-labelledby="run-card-notes">
        <div className="print-section-title" id="run-card-notes">General Notes</div>
        <div className="print-notes" role="textbox" aria-label="General notes">
          {notes || "(none provided)"}
        </div>
      </section>
    </PrintLayout>
  );
}
