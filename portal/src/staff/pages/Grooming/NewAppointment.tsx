import { useRef, useState } from "react";

import OwnerPicker from "../../components/OwnerPicker";
import PetPicker from "../../components/PetPicker";
import { createGroom, getGroomAvailability } from "../../lib/fetchers";

export default function NewGroom() {
  const formRef = useRef<HTMLFormElement>(null);
  const [ownerId, setOwnerId] = useState<string>();
  const [petId, setPetId] = useState<string>();
  const [slots, setSlots] = useState<any[]>([]);

  const findSlots = async () => {
    const form = new FormData(formRef.current!);
    const params = {
      date_from: String(form.get("date")),
      date_to: String(form.get("date")),
      service_id: String(form.get("service_id") || ""),
      location_id: String(form.get("location_id") || ""),
    };
    setSlots(await getGroomAvailability(params));
  };

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const form = new FormData(formRef.current!);
    const payload = {
      owner_id: ownerId,
      pet_id: petId,
      specialist_id: form.get("specialist_id"),
      service_id: form.get("service_id"),
      addon_ids: String(form.get("addon_ids") || "")
        .split(",")
        .filter(Boolean),
      start_at: new Date(String(form.get("start_at"))).toISOString(),
      notes: form.get("notes") || null,
      reservation_id: form.get("reservation_id") || null,
    };
    await createGroom(payload);
    alert("Appointment created");
  };

  return (
    <form
      ref={formRef}
      className="bg-white p-6 rounded-xl shadow grid gap-3 max-w-2xl"
      onSubmit={onSubmit}
    >
      <h3 className="text-xl font-semibold">Book grooming appointment</h3>
      <OwnerPicker onPick={setOwnerId} />
      <PetPicker ownerId={ownerId} onPick={setPetId} />
      <input name="location_id" placeholder="Location UUID" className="border rounded px-3 py-2" />
      <input name="specialist_id" placeholder="Specialist UUID" className="border rounded px-3 py-2" />
      <input name="service_id" placeholder="Service UUID" className="border rounded px-3 py-2" />
      <input
        name="addon_ids"
        placeholder="Addon UUIDs comma separated"
        className="border rounded px-3 py-2"
      />
      <label className="text-sm">
        Date
        <input type="date" name="date" className="border rounded px-3 py-2 w-full" />
      </label>
      <button
        type="button"
        className="bg-slate-900 text-white px-3 py-2 rounded"
        onClick={findSlots}
      >
        Find slots
      </button>
      {!!slots.length && (
        <ul className="text-sm list-disc pl-6">
          {slots.map((s, i) => (
            <li key={i}>{new Date(s.start_at).toLocaleString()}</li>
          ))}
        </ul>
      )}
      <label className="text-sm">
        Start at
        <input type="datetime-local" name="start_at" className="border rounded px-3 py-2 w-full" />
      </label>
      <input
        name="reservation_id"
        placeholder="Reservation UUID (optional)"
        className="border rounded px-3 py-2"
      />
      <textarea name="notes" placeholder="Notes" className="border rounded px-3 py-2" />
      <button className="bg-orange-500 text-white px-4 py-2 rounded">Book</button>
    </form>
  );
}
