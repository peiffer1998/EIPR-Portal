import api from "../../lib/api";
import { P } from "./paths";

const ok = <T>(p: Promise<{ data: T }>): Promise<T> => p.then((r) => r.data);

// Owners & Pets
export const listOwners = (q?: string) =>
  ok<any[]>(api.get(P.owners.list, { params: { q, limit: 50 } }));
export const getOwner = (id: string) => ok<any>(api.get(P.owners.byId(id)));
export const getOwnerPets = (id: string) => ok<any[]>(api.get(P.owners.pets(id)));
export const listPets = (owner_id?: string, q?: string) =>
  ok<any[]>(api.get(P.pets.list, { params: { owner_id, q, limit: 50 } }));
export const getPet = (id: string) => ok<any>(api.get(P.pets.byId(id)));
export const getPetVax = (id: string) =>
  ok<any[]>(api.get(P.pets.vax(id)).catch(() => ({ data: [] } as any)));

// Reservations & Grooming
export const listReservations = (params: any) =>
  ok<any[]>(api.get(P.reservations.base, { params }));
export const createReservation = (payload: any) =>
  ok<any>(api.post(P.reservations.base, payload));
export const createGroom = (payload: any) => ok<any>(api.post(P.grooming.appts, payload));
export const getGroomAvailability = (params: any) =>
  ok<any[]>(api.get(P.grooming.availability, { params }));

// Reports JSON fallbacks if you don’t have CSV yet
export const jsonRevenue = (a: string, b: string) =>
  ok<any>(api.get("/reports/revenue", { params: { start_date: a, end_date: b } }));
export const jsonOccupancy = (a: string, b: string) =>
  ok<any[]>(api.get("/reports/occupancy", { params: { start_date: a, end_date: b } }));

// Staff tools (Phase 13)
export const timeclockPunchIn = (location_id: string) =>
  ok<any>(api.post(`${P.staff.timeclock}/punch-in`, null, { params: { location_id } }));
export const timeclockPunchOut = () => ok<any>(api.post(`${P.staff.timeclock}/punch-out`));
export const listTips = () => ok<any[]>(api.get(P.staff.tips));
export const createTip = (payload: any) => ok<any>(api.post(P.staff.tips, payload));
export const buildCommissions = (date_from: string, date_to: string) =>
  ok<{ created: number }>(
    api.post(`${P.staff.commissions}/build`, null, { params: { date_from, date_to } }),
  );
export const listCommissions = () => ok<any[]>(api.get(P.staff.commissions));
export const openPeriod = (payload: any) => ok<any>(api.post(P.staff.payroll, payload));
export const lockPeriod = (id: string) =>
  ok<any>(api.post(`${P.staff.payroll}/${id}/lock`));
export const markPaid = (id: string) =>
  ok<any>(api.post(`${P.staff.payroll}/${id}/mark-paid`));
