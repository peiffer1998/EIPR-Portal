import api from "../../lib/api";
const ok = <T>(p:Promise<{data:T}>):Promise<T> => p.then(r=>r.data);

/** Capacity rules (per location)
 *  GET    /locations/{location_id}/capacity-rules
 *  POST   /locations/{location_id}/capacity-rules
 *  PATCH  /locations/{location_id}/capacity-rules/{rule_id}
 *  DELETE /locations/{location_id}/capacity-rules/{rule_id}
 */
export async function listCapacityRules(location_id: string){
  return ok<any[]>(api.get(`/locations/${location_id}/capacity-rules`));
}
export async function createCapacityRule(location_id: string, payload: { reservation_type:"boarding"|"daycare"|"grooming"; max_active:number|null; waitlist_limit:number|null }){
  return ok<any>(api.post(`/locations/${location_id}/capacity-rules`, { ...payload, location_id }));
}
export async function updateCapacityRule(location_id: string, rule_id: string, patch: { max_active?:number|null; waitlist_limit?:number|null }){
  return ok<any>(api.patch(`/locations/${location_id}/capacity-rules/${rule_id}`, patch));
}
export async function deleteCapacityRule(location_id: string, rule_id: string){
  await api.delete(`/locations/${location_id}/capacity-rules/${rule_id}`);
  return true;
}

/** Daily availability
 * GET /reservations/availability/daily?location_id=...&reservation_type=...&start_date=YYYY-MM-DD&end_date=YYYY-MM-DD
 */
export async function getDailyAvailability(location_id: string, reservation_type:"boarding"|"daycare"|"grooming", start_date: string, end_date: string){
  return ok<{ location_id:string; reservation_type:string; days:{ date:string; capacity:number|null; booked:number; available:number|null }[] }>(
    api.get(`/reservations/availability/daily`, { params:{ location_id, reservation_type, start_date, end_date }})
  );
}
