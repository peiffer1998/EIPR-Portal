import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { getOwner, getOwnerPets, listReservations } from "../../lib/fetchers";
import EditableInfoCard from "../../components/EditableInfoCard";
import NoteList from "../../components/NoteList";
import FileUploader from "../../components/FileUploader";
import { updateOwner, listOwnerNotes, addOwnerNote, listOwnerFiles, uploadOwnerFile } from "../../lib/crmFetchers";

export default function OwnerProfile() {
  const { ownerId = "" } = useParams();

  const owner = useQuery({
    queryKey: ["owner", ownerId],
    queryFn: () => getOwner(ownerId),
    enabled: Boolean(ownerId),
  });
  const pets = useQuery({
    queryKey: ["ownerPets", ownerId],
    queryFn: () => getOwnerPets(ownerId),
    enabled: Boolean(ownerId),
  });
  const reservations = useQuery({
    queryKey: ["ownerResv", ownerId],
    queryFn: () => listReservations({ owner_id: ownerId, limit: 50 }),
    enabled: Boolean(ownerId),
  });

  if (owner.isLoading) return <div>Loading...</div>;
  if (owner.isError) return <div className="text-red-600 text-sm">Failed to load owner</div>;

  const o: any = owner.data || {};

  return (
    <div className="grid gap-4">
      <EditableInfoCard
        key={o.id || ownerId}
        title="Owner"
        initial={o}
        fields={[
          { name: "first_name", label: "First name" },
          { name: "last_name", label: "Last name" },
          { name: "email", label: "Email", type: "email" },
          { name: "phone", label: "Phone" },
          { name: "address1", label: "Address 1" },
          { name: "address2", label: "Address 2" },
          { name: "city", label: "City" },
          { name: "state", label: "State" },
          { name: "postal_code", label: "Postal code" },
        ]}
        onSave={async (vals) => {
          await updateOwner(ownerId, vals);
          await owner.refetch();
        }}
      />

      <div className="bg-white p-6 rounded-xl shadow">
        <h4 className="font-semibold mb-2">Pets</h4>
        <ul className="list-disc pl-6 text-sm">
          {(pets.data || []).map((p: any) => (
            <li key={p.id}>
              <Link className="text-blue-700" to={`/staff/pets/${p.id}`}>
                {p.name}
              </Link>{" "}
              • {p.breed || p.species}
            </li>
          ))}
        </ul>
      </div>

      <div className="bg-white p-6 rounded-xl shadow">
        <h4 className="font-semibold mb-2">Recent reservations</h4>
        <ul className="text-sm space-y-1">
          {(reservations.data || []).slice(0, 10).map((r: any) => (
            <li key={r.id}>
              {r.reservation_type} • {new Date(r.start_at).toLocaleString()} → {" "}
              {new Date(r.end_at).toLocaleString()}
            </li>
          ))}
        </ul>
      </div>

      <NoteList
        fetchNotes={() => listOwnerNotes(ownerId)}
        addNote={(text) => addOwnerNote(ownerId, text)}
      />

      <FileUploader
        title="Owner Files"
        list={() => listOwnerFiles(ownerId)}
        upload={(file) => uploadOwnerFile(ownerId, file)}
      />
    </div>
  );
}
