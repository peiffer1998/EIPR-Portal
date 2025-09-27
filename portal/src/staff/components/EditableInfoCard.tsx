import { useState } from "react";
export default function EditableInfoCard({ title, fields, initial, onSave }:{
  title:string;
  fields:{ name:string; label:string; type?:string; placeholder?:string }[];
  initial:any;
  onSave:(values:any)=>Promise<void>;
}){
  const [values,setValues]=useState<any>(initial||{}); const [edit,setEdit]=useState(false); const [busy,setBusy]=useState(false); const [err,setErr]=useState<string|null>(null);
  return (
    <div className="bg-white p-6 rounded-xl shadow">
      <div className="flex items-center justify-between">
        <h3 className="text-xl font-semibold">{title}</h3>
        <button className="text-sm px-3 py-1 rounded bg-slate-900 text-white" onClick={()=>setEdit(!edit)}>{edit?"Cancel":"Edit"}</button>
      </div>
      {!edit ? (
        <div className="mt-3 grid md:grid-cols-2 gap-3 text-sm">
          {fields.map(f=> <div key={f.name}><div className="text-slate-500">{f.label}</div><div className="font-medium">{values?.[f.name] ?? ""}</div></div>)}
        </div>
      ) : (
        <form className="mt-3 grid md:grid-cols-2 gap-3" onSubmit={async e=>{e.preventDefault(); setBusy(true); setErr(null); try{ await onSave(values); setEdit(false);}catch(x:any){ setErr(x?.response?.data?.detail||x?.message||"Save failed"); }finally{ setBusy(false); }}}>
          {fields.map(f=> <label key={f.name} className="text-sm grid gap-1">
            <span className="text-slate-600">{f.label}</span>
            <input className="border rounded px-3 py-2" type={f.type||"text"} placeholder={f.placeholder||""} value={values?.[f.name]||""} onChange={e=>setValues({...values,[f.name]:e.target.value})}/>
          </label>)}
          <div className="col-span-full">
            <button disabled={busy} className="bg-orange-500 text-white px-4 py-2 rounded">{busy?"Saving…":"Save"}</button>
            {err && <span className="text-sm text-red-600 ml-3">{err}</span>}
          </div>
        </form>
      )}
    </div>
  );
}
