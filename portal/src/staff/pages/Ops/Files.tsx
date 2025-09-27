import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import DocPreview from "../../components/DocPreview";
import DocTable from "../../components/DocTable";
import DocUpload from "../../components/DocUpload";
import {
  deleteDocument,
  finalizeDocument,
  listDocuments,
  uploadDocument,
} from "../../lib/documentsFetchers";

interface Filters {
  type?: string;
  q?: string;
  date_from?: string;
  date_to?: string;
}

export default function FilesPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<Filters>({});
  const [previewId, setPreviewId] = useState<string | null>(null);

  const listQuery = useQuery({
    queryKey: ["documents", filters],
    queryFn: () => listDocuments(filters),
    staleTime: 5_000,
  });

  const upload = useMutation({
    mutationFn: ({ file, opts }: { file: File; opts: { owner_id?: string; pet_id?: string; kind?: string } }) =>
      uploadDocument(file, opts),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });

  const finalize = useMutation({
    mutationFn: (id: string) => finalizeDocument(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });

  const destroy = useMutation({
    mutationFn: (id: string) => deleteDocument(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents"] }),
  });

  const rows = useMemo(() => listQuery.data || [], [listQuery.data]);

  return (
    <div className="grid gap-3">
      <div className="bg-white p-3 rounded-xl shadow grid md:grid-cols-5 gap-2 items-end">
        <label className="text-sm grid">
          <span>Type</span>
          <select
            className="border rounded px-3 py-2"
            value={filters.type ?? ""}
            onChange={(event) => setFilters((prev) => ({ ...prev, type: event.target.value || undefined }))}
          >
            <option value="">Any</option>
            <option value="image">Image</option>
            <option value="pdf">PDF</option>
            <option value="vaccination">Vaccination</option>
            <option value="agreement">Agreement</option>
          </select>
        </label>
        <label className="text-sm grid">
          <span>From</span>
          <input
            className="border rounded px-3 py-2"
            type="date"
            value={filters.date_from ?? ""}
            onChange={(event) => setFilters((prev) => ({ ...prev, date_from: event.target.value || undefined }))}
          />
        </label>
        <label className="text-sm grid">
          <span>To</span>
          <input
            className="border rounded px-3 py-2"
            type="date"
            value={filters.date_to ?? ""}
            onChange={(event) => setFilters((prev) => ({ ...prev, date_to: event.target.value || undefined }))}
          />
        </label>
        <label className="text-sm grid md:col-span-2">
          <span>Search</span>
          <input
            className="border rounded px-3 py-2"
            placeholder="file name, owner, pet"
            value={filters.q ?? ""}
            onChange={(event) => setFilters((prev) => ({ ...prev, q: event.target.value || undefined }))}
          />
        </label>
      </div>

      <DocUpload onUpload={(file, opts) => upload.mutateAsync({ file, opts })} />

      <DocTable
        rows={rows}
        onPreview={(id) => setPreviewId(id)}
        onFinalize={(id) => finalize.mutateAsync(id)}
        onDelete={(id) => destroy.mutateAsync(id)}
      />

      {previewId && <DocPreview id={previewId} onClose={() => setPreviewId(null)} />}
    </div>
  );
}
