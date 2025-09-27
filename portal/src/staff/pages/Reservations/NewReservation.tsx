import { useRef, useState } from "react";

import OwnerPicker from "../../components/OwnerPicker";
import PetPicker from "../../components/PetPicker";
import { createReservation } from "../../lib/fetchers";

export default function NewReservation() {
  const formRef = useRef<HTMLFormElement>(null);
  const [ownerId, setOwnerId] = useState<string>();
  const [petId, setPetId] = useState<string>();

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const form = new FormData(formRef.current!);
    const payload = {
      pet_id: petId,
      location_id: form.get("location_id"),
      reservation_type: form.get("reservation_type"),
      start_at: new Date(String(form.get("start_at"))).toISOString(),
      end_at: new Date(String(form.get("end_at"))).toISOString(),
      base_rate: form.get("base_rate") || "0",
      notes: form.get("notes") || null,
      kennel_id: form.get("kennel_id") || null,
    };
    await createReservation(payload);
    alert("Reservation created");
  };

  return (
    <form
      ref={formRef}
      className="bg-white p-6 rounded-xl shadow grid gap-3 max-w-2xl"
      onSubmit={onSubmit}
    >
      <h3 className="text-xl font-semibold">Create reservation</h3>
      <OwnerPicker onPick={setOwnerId} />
      <PetPicker ownerId={ownerId} onPick={setPetId} />
      <input name="location_id" placeholder="Location UUID" className="border rounded px-3 py-2" />
      <select name="reservation_type" className="border rounded px-3 py-2">
        <option>BOARDING</option>
        <option>DAYCARE</option>
      </select>
      <label className="text-sm">
        Start at
        <input type="datetime-local" name="start_at" className="border rounded px-3 py-2 w-full" />
      </label>
      <label className="text-sm">
        End at
        <input type="datetime-local" name="end_at" className="border rounded px-3 py-2 w-full" />
      </label>
      <input name="base_rate" placeholder="Base rate" className="border rounded px-3 py-2" />
      <input name="kennel_id" placeholder="Kennel UUID (optional)" className="border rounded px-3 py-2" />
      <textarea name="notes" placeholder="Notes" className="border rounded px-3 py-2" />
      <button className="bg-orange-500 text-white px-4 py-2 rounded">Create</button>
    </form>
  );
}
