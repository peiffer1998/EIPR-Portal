import { useEffect, useState } from "react";
import LocationSelect from "../../components/LocationSelect";
import RuleEditor from "../../components/RuleEditor";
import { createCapacityRule, deleteCapacityRule, listCapacityRules, updateCapacityRule } from "../../lib/capacityFetchers";

export default function AdminCapacity(){
  const [loc,setLoc]=useState<string>(localStorage.getItem("defaultLocationId")||"");
  const [rows,setRows]=useState<any[]>([]);
  const load=async(id:string)=> setRows(await listCapacityRules(id).catch(()=>[]));
  useEffect(()=>{ if(loc){ void load(loc); }},[loc]);

  return (
    <div className="grid gap-3">
      <div className="bg-white p-3 rounded-xl shadow flex items-end gap-2">
        <div className="text-sm text-slate-600">Location</div>
        <LocationSelect value={loc} onChange={(id)=>{ setLoc(id); localStorage.setItem("defaultLocationId", id); }}/>
      </div>
      {!loc ? <div className="text-sm text-slate-500">Pick a location to manage capacity rules.</div> :
      <RuleEditor
        rows={rows}
        onCreate={async(v)=>{ await createCapacityRule(loc, v); await load(loc); }}
        onUpdate={async(id,patch)=>{ await updateCapacityRule(loc,id,patch); await load(loc); }}
        onDelete={async(id)=>{ await deleteCapacityRule(loc,id); await load(loc); }}
      />}
    </div>
  );
}
