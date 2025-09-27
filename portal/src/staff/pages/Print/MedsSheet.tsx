import { useMemo } from "react";
import { useLocation, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import PrintLayout from "../../../print/PrintLayout";
import { getMedsBoard } from "../../lib/boardFetchers";

export default function MedsSheet() {
  const { date = "" } = useParams();
  const search = useLocation().search;
  const locationId = new URLSearchParams(search).get("location_id") || "";

  const { data } = useQuery({
    queryKey: ["meds-print", date, locationId],
    queryFn: () => getMedsBoard(date, locationId),
    enabled: Boolean(date && locationId),
  });

  const rows = useMemo(() => (Array.isArray(data) ? data : []), [data]);

  return (
    <PrintLayout
      title="Medication Sheet"
      meta={[
        { label: "Date", value: date },
        { label: "Location", value: locationId || "All" },
        { label: "Count", value: rows.length },
      ]}
    >
      <section className="print-block" aria-labelledby="meds-table">
        <div className="print-section-title" id="meds-table">Medication Schedule</div>
        <table className="print-table">
          <thead>
            <tr>
              <th scope="col">Pet</th>
              <th scope="col">Medication</th>
              <th scope="col">Dosage</th>
              <th scope="col">Frequency</th>
              <th scope="col">Instructions</th>
              <th scope="col">Initial</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row: any) => (
              <tr key={row.id ?? `${row.reservation_id}-${row.medication}`}> 
                <td>{row.pet?.name ?? row.reservation_id}</td>
                <td>{row.medication ?? row.name ?? ""}</td>
                <td>{row.dosage ?? row.amount ?? ""}</td>
                <td>{row.frequency ?? row.schedule ?? ""}</td>
                <td>{row.notes ?? row.instructions ?? ""}</td>
                <td style={{ width: "18%" }}>_______</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", color: "var(--print-muted)" }}>
                  No medications for this selection.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </PrintLayout>
  );
}
