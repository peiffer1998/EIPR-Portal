import api from "../../lib/api";
const ok = <T>(p:Promise<{data:T}>):Promise<T> => p.then(r=>r.data);
export const listLocations = ()=> ok<any[]>(api.get("/locations", { params:{ limit:100 }})).catch(()=>[]);
