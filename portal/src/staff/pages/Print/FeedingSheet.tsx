import { useMemo } from "react";
import { useLocation, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import PrintLayout from "../../../print/PrintLayout";
import { getFeedingBoard } from "../../lib/boardFetchers";

export default function FeedingSheet() {
  const { date = "" } = useParams();
  const search = useLocation().search;
  const locationId = new URLSearchParams(search).get("location_id") || "";

  const { data } = useQuery({
    queryKey: ["feeding-print", date, locationId],
    queryFn: () => getFeedingBoard(date, locationId),
    enabled: Boolean(date && locationId),
  });

  const rows = useMemo(() => (Array.isArray(data) ? data : []), [data]);

  return (
    <PrintLayout
      title="Feeding Sheet"
      meta={[
        { label: "Date", value: date },
        { label: "Location", value: locationId || "All" },
        { label: "Count", value: rows.length },
      ]}
    >
      <section className="print-block" aria-labelledby="feeding-table">
        <div className="print-section-title" id="feeding-table">Feeding Schedule</div>
        <table className="print-table">
          <thead>
            <tr>
              <th scope="col">Pet</th>
              <th scope="col">Run</th>
              <th scope="col">Time</th>
              <th scope="col">Food</th>
              <th scope="col">Amount</th>
              <th scope="col">Notes</th>
              <th scope="col">Initial</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row: any) => (
              <tr key={row.id ?? `${row.reservation_id}-${row.time}`}> 
                <td>{row.pet?.name ?? row.reservation_id}</td>
                <td>{row.run?.name ?? ""}</td>
                <td>{row.time ?? ""}</td>
                <td>{row.food ?? ""}</td>
                <td>{row.amount ?? ""}</td>
                <td>{row.notes ?? ""}</td>
                <td style={{ width: "14%" }}>_______</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={7} style={{ textAlign: "center", color: "var(--print-muted)" }}>
                  No feeding items for this selection.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>
    </PrintLayout>
  );
}
