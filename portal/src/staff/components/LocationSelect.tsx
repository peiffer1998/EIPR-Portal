import { useEffect, useState } from "react";
import { listLocations } from "../lib/adminFetchers";
export default function LocationSelect({ value, onChange }:{ value?:string; onChange:(id:string)=>void }){
  const [locs,setLocs]=useState<any[]>([]);
  useEffect(()=>{ void listLocations().then(setLocs).catch(()=>{}); },[]);
  return (
    <select className="border rounded px-3 py-2 min-w-[220px]" value={value||""} onChange={e=>onChange(e.target.value)}>
      <option value="">Pick a location</option>
      {locs.map((l:any)=><option key={l.id} value={l.id}>{l.name||l.id}</option>)}
    </select>
  );
}
