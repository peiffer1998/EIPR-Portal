export default function RuleEditor({ rows, onCreate, onUpdate, onDelete }:{
  rows: any[];
  onCreate:(vals:{ reservation_type:"boarding"|"daycare"|"grooming"; max_active:number|null; waitlist_limit:number|null })=>Promise<void>;
  onUpdate:(id:string, patch:{ max_active?:number|null; waitlist_limit?:number|null })=>Promise<void>;
  onDelete:(id:string)=>Promise<void>;
}){
  return (
    <div className="bg-white rounded-xl shadow overflow-auto">
      <table className="w-full text-sm">
        <thead><tr className="text-left text-slate-500">
          <th className="px-3 py-2">Service</th><th>Max active</th><th>Waitlist limit</th><th>Actions</th>
        </tr></thead>
        <tbody>
          {rows.map((r:any)=>(
            <tr key={r.id} className="border-t">
              <td className="px-3 py-2">{(r.reservation_type||"").toUpperCase()}</td>
              <td><input className="border rounded px-2 py-1 w-24" type="number" placeholder="none" defaultValue={r.max_active ?? ""} onBlur={e=>onUpdate(r.id, { max_active: e.target.value===""? null : Number(e.target.value) })}/></td>
              <td><input className="border rounded px-2 py-1 w-24" type="number" placeholder="none" defaultValue={r.waitlist_limit ?? ""} onBlur={e=>onUpdate(r.id, { waitlist_limit: e.target.value===""? null : Number(e.target.value) })}/></td>
              <td><button className="text-xs text-red-600" onClick={()=>onDelete(r.id)}>Delete</button></td>
            </tr>
          ))}
          <tr className="border-t bg-slate-50">
            <td className="px-3 py-2">
              <select id="new_svc" className="border rounded px-2 py-1">
                <option value="boarding">BOARDING</option><option value="daycare">DAYCARE</option><option value="grooming">GROOMING</option>
              </select>
            </td>
            <td><input id="new_max" className="border rounded px-2 py-1 w-24" type="number" placeholder="none"/></td>
            <td><input id="new_wait" className="border rounded px-2 py-1 w-24" type="number" placeholder="none"/></td>
            <td><button className="text-xs bg-slate-900 text-white px-2 py-1 rounded" onClick={async()=>{
              const svc=(document.getElementById("new_svc") as HTMLSelectElement).value as any;
              const maxStr=(document.getElementById("new_max") as HTMLInputElement).value;
              const waitStr=(document.getElementById("new_wait") as HTMLInputElement).value;
              await onCreate({ reservation_type:svc, max_active: maxStr===""? null : Number(maxStr), waitlist_limit: waitStr===""? null : Number(waitStr) });
              (document.getElementById("new_max") as HTMLInputElement).value="";
              (document.getElementById("new_wait") as HTMLInputElement).value="";
            }}>Add</button></td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}
