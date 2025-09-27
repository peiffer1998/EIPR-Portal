import { useParams, Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type ChangeEvent } from "react";

import { getPet, getPetVax, listReservations } from "../../lib/fetchers";
import EditableInfoCard from "../../components/EditableInfoCard";
import VaccineEditor from "../../components/VaccineEditor";
import NoteList from "../../components/NoteList";
import DocTable from "../../components/DocTable";
import DocPreview from "../../components/DocPreview";
import { listDocuments, uploadDocument, finalizeDocument, deleteDocument } from "../../lib/documentsFetchers";
import { updatePet, addVaccine, deleteVaccine, listPetNotes, addPetNote } from "../../lib/crmFetchers";

function PetDocuments({ petId }: { petId: string }) {
  const queryClient = useQueryClient();
  const [previewId, setPreviewId] = useState<string | null>(null);

  const docs = useQuery({
    queryKey: ["petDocs", petId],
    queryFn: () => listDocuments({ pet_id: petId }),
    enabled: Boolean(petId),
  });

  const upload = useMutation({
    mutationFn: (file: File) => uploadDocument(file, { pet_id: petId }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["petDocs", petId] }),
  });

  const finalize = useMutation({
    mutationFn: (id: string) => finalizeDocument(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["petDocs", petId] }),
  });

  const destroy = useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["petDocs", petId] }),
  });

  async function handleUpload(event: ChangeEvent<HTMLInputElement>) {
    if (!event.target.files?.length) return;
    const file = event.target.files[0];
    await upload.mutateAsync(file);
    event.target.value = "";
  }

  return (
    <div className="grid gap-3">
      <label className="text-sm grid w-fit">
        <span>Upload document</span>
        <input className="border rounded px-3 py-2" type="file" onChange={handleUpload} />
      </label>

      <DocTable
        rows={docs.data || []}
        onPreview={(id) => setPreviewId(id)}
        onFinalize={(id) => finalize.mutateAsync(id)}
        onDelete={(id) => destroy.mutateAsync(id)}
      />

      {previewId && <DocPreview id={previewId} onClose={() => setPreviewId(null)} />}
    </div>
  );
}

export default function PetProfile() {
  const { petId = "" } = useParams();

  const pet = useQuery({
    queryKey: ["pet", petId],
    queryFn: () => getPet(petId),
    enabled: Boolean(petId),
  });
  const reservations = useQuery({
    queryKey: ["resv", petId],
    queryFn: () => listReservations({ pet_id: petId, limit: 50 }),
    enabled: Boolean(petId),
  });

  if (pet.isLoading) return <div>Loading...</div>;
  if (pet.isError) return <div className="text-red-600 text-sm">Failed to load pet</div>;

  const p: any = pet.data || {};

  return (
    <div className="grid gap-4">
      <EditableInfoCard
        key={p.id || petId}
        title="Pet"
        initial={p}
        fields={[
          { name: "name", label: "Name" },
          { name: "breed", label: "Breed" },
          { name: "species", label: "Species" },
          { name: "color", label: "Color" },
          { name: "sex", label: "Sex" },
          { name: "weight", label: "Weight" },
        ]}
        onSave={async (vals) => {
          await updatePet(petId, vals);
          await pet.refetch();
        }}
      />

      <div className="bg-white p-6 rounded-xl shadow">
        <h3 className="text-xl font-semibold mb-1">{p.name}</h3>
        <div className="text-sm text-slate-600">
          {p.breed || p.species} • {p.color} • {p.sex}
        </div>
        {p.owner_id ? (
          <div className="text-sm mt-2">
            Owner {" "}
            <Link className="text-blue-700" to={`/staff/customers/${p.owner_id}`}>
              {p.owner?.first_name && p.owner?.last_name
                ? `${p.owner.first_name} ${p.owner.last_name}`
                : p.owner_id}
            </Link>
          </div>
        ) : null}
      </div>

      <VaccineEditor
        list={() => getPetVax(petId)}
        add={(payload) => addVaccine(petId, payload)}
        remove={(vaccineId) => deleteVaccine(petId, vaccineId)}
      />

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
        fetchNotes={() => listPetNotes(petId)}
        addNote={(text) => addPetNote(petId, text)}
      />

      <div className="bg-white p-6 rounded-xl shadow">
        <h4 className="font-semibold mb-2">Documents</h4>
        <PetDocuments petId={petId} />
      </div>
    </div>
  );
}
