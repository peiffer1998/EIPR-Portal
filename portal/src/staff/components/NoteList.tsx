import { useCallback, useEffect, useState } from "react";
export default function NoteList({ fetchNotes, addNote }:{
  fetchNotes:()=>Promise<any[]>;
  addNote:(text:string)=>Promise<any>;
}){
  const [items,setItems]=useState<any[]>([]); const [text,setText]=useState(""); const [busy,setBusy]=useState(false);
  const load = useCallback(async () => setItems(await fetchNotes()), [fetchNotes]);
  useEffect(() => { void load(); }, [load]);
  return (
    <div className="bg-white p-6 rounded-xl shadow">
      <h4 className="font-semibold mb-2">Notes</h4>
      <div className="flex gap-2 mb-2">
        <input className="border rounded px-3 py-2 flex-1" placeholder="Add note..." value={text} onChange={e=>setText(e.target.value)}/>
        <button className="bg-slate-900 text-white px-3 py-2 rounded" disabled={!text||busy} onClick={async()=>{ setBusy(true); await addNote(text); setText(""); await load(); setBusy(false); }}>Add</button>
      </div>
      <ul className="text-sm space-y-2">{items.map((n:any)=>(<li key={n.id} className="border rounded p-2">{n.text || n.note || JSON.stringify(n)}</li>))}</ul>
    </div>
  );
}
