import api from "../../lib/api";
const ok = <T>(p:Promise<{data:T}>):Promise<T> => p.then(r=>r.data);

export const getReservation = (id:string)=> ok<any>(api.get(`/reservations/${id}`));
export const updateReservation = (id:string, payload:any)=> ok<any>(api.patch(`/reservations/${id}`, payload));
export const cancelReservation = (id:string, reason?:string)=> ok<any>(api.post(`/reservations/${id}/cancel`, { reason }).catch(()=>api.patch(`/reservations/${id}`, { status:"CANCELED", cancel_reason:reason } ).then(r=>r)));
export const noShowReservation = (id:string)=> ok<any>(api.post(`/reservations/${id}/no-show`).catch(()=>api.patch(`/reservations/${id}`, { status:"NO_SHOW" }).then(r=>r)));
export const checkIn = (id:string, run_id?:string)=> ok<any>(api.post(`/reservations/${id}/check-in`, { run_id }).catch(()=>api.patch(`/reservations/${id}`, { status:"CHECKED_IN", run_id }).then(r=>r)));
export const checkOut = (id:string)=> ok<any>(api.post(`/reservations/${id}/check-out`).catch(()=>api.patch(`/reservations/${id}`, { status:"CHECKED_OUT" }).then(r=>r)));
export const moveRun = (id:string, run_id:string)=> ok<any>(api.post(`/reservations/${id}/move-run`, { run_id }).catch(()=>api.patch(`/reservations/${id}`, { run_id }).then(r=>r)));
export const listRuns = (location_id:string)=> ok<any[]>(api.get(`/runs`, { params:{ location_id, limit:200 }}));
export const capacityWindow = (location_id:string, start:string, end:string, reservation_type?:string)=> ok<any[]>(api.get(`/reports/occupancy`, { params:{ start_date:start, end_date:end, location_id, reservation_type }}));
