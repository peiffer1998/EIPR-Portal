import { useEffect, useMemo } from "react";
import { useLocation, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

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

  useEffect(() => {
    if (date && locationId) {
      const handle = setTimeout(() => window.print(), 100);
      return () => clearTimeout(handle);
    }
    return undefined;
  }, [date, locationId, rows.length]);

  return (
    <div style={{ fontFamily: "ui-sans-serif", padding: "24px" }}>
      <h1 style={{ fontSize: "24px", marginBottom: "4px" }}>Feeding Sheet</h1>
      <div style={{ color: "#475569", marginBottom: "16px" }}>
        Date: <strong>{date}</strong> • Location: <strong>{locationId}</strong>
      </div>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "13px" }}>
        <thead>
          <tr>
            <th align="left" style={{ borderBottom: "1px solid #cbd5f5", padding: "6px" }}>Pet</th>
            <th align="left" style={{ borderBottom: "1px solid #cbd5f5", padding: "6px" }}>Run</th>
            <th align="left" style={{ borderBottom: "1px solid #cbd5f5", padding: "6px" }}>Time</th>
            <th align="left" style={{ borderBottom: "1px solid #cbd5f5", padding: "6px" }}>Food</th>
            <th align="left" style={{ borderBottom: "1px solid #cbd5f5", padding: "6px" }}>Amount</th>
            <th align="left" style={{ borderBottom: "1px solid #cbd5f5", padding: "6px" }}>Notes</th>
            <th align="left" style={{ borderBottom: "1px solid #cbd5f5", padding: "6px" }}>Given</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row: any) => (
            <tr key={row.id}>
              <td style={{ borderBottom: "1px solid #e2e8f0", padding: "6px" }}>{row.pet?.name || row.reservation_id}</td>
              <td style={{ borderBottom: "1px solid #e2e8f0", padding: "6px" }}>{row.run?.name || ""}</td>
              <td style={{ borderBottom: "1px solid #e2e8f0", padding: "6px" }}>{row.time || ""}</td>
              <td style={{ borderBottom: "1px solid #e2e8f0", padding: "6px" }}>{row.food || ""}</td>
              <td style={{ borderBottom: "1px solid #e2e8f0", padding: "6px" }}>{row.amount || ""}</td>
              <td style={{ borderBottom: "1px solid #e2e8f0", padding: "6px" }}>{row.notes || ""}</td>
              <td style={{ borderBottom: "1px solid #e2e8f0", padding: "6px" }}>___</td>
            </tr>
          ))}
          {rows.length === 0 ? (
            <tr>
              <td colSpan={7} style={{ padding: "12px", color: "#64748b" }}>
                No feeding items for this selection.
              </td>
            </tr>
          ) : null}
        </tbody>
      </table>
    </div>
  );
}
