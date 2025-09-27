import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getReservation } from "../../lib/reservationOps";
export default function PrintRunCard(){
  const { reservationId="" } = useParams();
  const rs = useQuery({ queryKey:["resv",reservationId], queryFn:()=>getReservation(reservationId), enabled:Boolean(reservationId) });
  const r:any = rs.data || {};
  return (
    <div style={{fontFamily:"ui-sans-serif", padding:"20px"}}>
      <h1>Run Card</h1>
      <div>Reservation: {reservationId}</div>
      <div>Pet: {r.pet?.name || r.pet_id}</div>
      <div>Owner: {r.owner?.first_name} {r.owner?.last_name}</div>
      <div>Dates: {r.start_at} → {r.end_at}</div>
      <div>Run: {r.run?.name || r.run_id || "Unassigned"}</div>
      <hr/>
      <div><strong>Feeding</strong></div>
      <div><strong>Medications</strong></div>
      <div><strong>Notes</strong></div>
      <script>window.print()</script>
    </div>
  );
}
