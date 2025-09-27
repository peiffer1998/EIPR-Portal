import { useRef, useState, type ChangeEvent } from "react";

import OwnerPicker from "./OwnerPicker";
import PetPicker from "./PetPicker";

interface Props {
  onUpload: (file: File, opts: { owner_id?: string; pet_id?: string; kind?: string }) => Promise<void>;
}

export default function DocUpload({ onUpload }: Props) {
  const [ownerId, setOwnerId] = useState<string>("");
  const [petId, setPetId] = useState<string>("");
  const [kind, setKind] = useState<string>("generic");
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleChange(event: ChangeEvent<HTMLInputElement>) {
    if (!event.target.files?.length) return;
    const file = event.target.files[0];
    await onUpload(file, {
      owner_id: ownerId || undefined,
      pet_id: petId || undefined,
      kind: kind || undefined,
    });
    if (inputRef.current) inputRef.current.value = "";
  }

  return (
    <div className="bg-white p-4 rounded-xl shadow grid md:grid-cols-5 gap-2 items-end">
      <div className="md:col-span-2">
        <OwnerPicker onPick={setOwnerId} />
      </div>
      <div className="md:col-span-2">
        <PetPicker ownerId={ownerId} onPick={setPetId} />
      </div>
      <label className="text-sm grid">
        <span>Kind</span>
        <select className="border rounded px-3 py-2" value={kind} onChange={(event) => setKind(event.target.value)}>
          <option value="generic">Generic</option>
          <option value="vaccination">Vaccination</option>
          <option value="agreement">Agreement</option>
          <option value="image">Image</option>
        </select>
      </label>
      <div className="md:col-span-5">
        <input ref={inputRef} type="file" onChange={handleChange} />
      </div>
    </div>
  );
}
