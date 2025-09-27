import api from "../../lib/api";
import { P } from "./paths";
const ok = <T>(p:Promise<{data:T}>):Promise<T> => p.then(r=>r.data);

// Owners
export const updateOwner = (id:string, payload:any)=> ok<any>(api.patch(P.owners.byId(id), payload));
export const createOwner = (payload:any)=> ok<any>(api.post(P.owners.list, payload));
export const mergeOwners = (srcId:string, dstId:string)=> ok<any>(api.post(`/owners/${srcId}/merge`, { into_owner_id: dstId }));

// Pets
export const updatePet = (id:string, payload:any)=> ok<any>(api.patch(P.pets.byId(id), payload));
export const createPet = (payload:any)=> ok<any>(api.post(P.pets.list, payload));

// Vaccines
export const addVaccine = (petId:string, payload:any)=> ok<any>(api.post(P.pets.vax(petId), payload));
export const deleteVaccine = (petId:string, vaccineId:string)=> ok<any>(api.delete(`${P.pets.vax(petId)}/${vaccineId}`));

// Notes
export const listOwnerNotes = (ownerId:string)=> ok<any[]>(api.get(`/owners/${ownerId}/notes`));
export const addOwnerNote = (ownerId:string, text:string)=> ok<any>(api.post(`/owners/${ownerId}/notes`, { text }));
export const listPetNotes = (petId:string)=> ok<any[]>(api.get(`/pets/${petId}/notes`));
export const addPetNote = (petId:string, text:string)=> ok<any>(api.post(`/pets/${petId}/notes`, { text }));

// Files (staff uploads)
export const listOwnerFiles = (ownerId:string)=> ok<any[]>(api.get(`/owners/${ownerId}/files`));
export const uploadOwnerFile = async (ownerId:string, file:File, kind="document")=>{
  const fd = new FormData(); fd.append("file", file); fd.append("kind", kind);
  const { data } = await api.post(`/owners/${ownerId}/files`, fd, { headers:{ "Content-Type":"multipart/form-data" }});
  return data;
};
