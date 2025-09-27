import { useCallback, useEffect, useState } from "react";
export default function VaccineEditor({ list, add, remove }:{
  list:()=>Promise<any[]>;
  add:(payload:any)=>Promise<any>;
  remove:(id:string)=>Promise<any>;
}){
  const [rows,setRows]=useState<any[]>([]); const [v,setV]=useState({ vaccine:"", given_on:"", expires_on:"" });
  const load = useCallback(async () => setRows(await list()), [list]);
  useEffect(() => { void load(); }, [load]);
  return (
    <div className="bg-white p-6 rounded-xl shadow">
      <h4 className="font-semibold mb-2">Vaccinations</h4>
      <div className="grid md:grid-cols-3 gap-2">
        <input className="border rounded px-3 py-2" placeholder="Vaccine" value={v.vaccine} onChange={e=>setV({...v, vaccine:e.target.value})}/>
        <input type="date" className="border rounded px-3 py-2" value={v.given_on} onChange={e=>setV({...v, given_on:e.target.value})}/>
        <input type="date" className="border rounded px-3 py-2" value={v.expires_on} onChange={e=>setV({...v, expires_on:e.target.value})}/>
      </div>
      <button className="mt-2 bg-slate-900 text-white px-3 py-2 rounded" disabled={!v.vaccine} onClick={async()=>{ await add(v); setV({ vaccine:"", given_on:"", expires_on:"" }); await load(); }}>Add</button>
      <table className="w-full text-sm mt-3">
        <thead><tr className="text-left text-slate-500"><th>Vaccine</th><th>Given</th><th>Expires</th><th/></tr></thead>
        <tbody>{rows.map((r:any)=>(<tr key={r.id||r.vaccine} className="border-t">
          <td className="py-2">{r.vaccine||r.name}</td><td>{r.given_on||r.given||""}</td><td>{r.expires_on||r.expires||""}</td>
          <td><button className="text-red-600 text-sm" onClick={async()=>{ await remove(r.id || r._id || r.vaccine); await load(); }}>Delete</button></td>
        </tr>))}</tbody>
      </table>
    </div>
  );
}
