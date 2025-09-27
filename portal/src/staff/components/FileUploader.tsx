import { useCallback, useEffect, useState } from "react";
export default function FileUploader({ list, upload, title="Files" }:{
  list:()=>Promise<any[]>;
  upload:(file:File)=>Promise<any>;
  title?:string;
}){
  const [items,setItems]=useState<any[]>([]);
  const [busy,setBusy]=useState(false);
  const load = useCallback(async () => setItems(await list()), [list]);
  useEffect(() => { void load(); }, [load]);
  return (
    <div className="bg-white p-6 rounded-xl shadow">
      <div className="flex items-center justify-between"><h4 className="font-semibold">{title}</h4></div>
      <div className="mt-2">
        <input type="file" onChange={async e=>{ const f=e.target.files?.[0]; if(!f) return; setBusy(true); await upload(f); await load(); setBusy(false); }}/>
      </div>
      <ul className="text-sm mt-2 space-y-1">{items.map((f:any)=><li key={f.id || f.key}>{f.name || f.filename || f.key}</li>)}</ul>
      {busy && <div className="text-sm text-slate-500 mt-2">Uploading…</div>}
    </div>
  );
}
