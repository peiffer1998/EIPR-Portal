import type { ChangeEvent, FormEvent } from 'react';
import { useMemo, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';

import { finalizeDocument, presignDocument, uploadDocumentBytes } from '../lib/portal';
import { usePortalMe } from '../lib/usePortalMe';
import { PORTAL_ME_QUERY_KEY } from '../lib/usePortalMe';
import { useAuth } from '../state/useAuth';

const Uploads = () => {
  const queryClient = useQueryClient();
  const { token, owner } = useAuth();
  const { data, isLoading } = usePortalMe();
  const documents = useMemo(() => data?.documents ?? [], [data]);
  const pets = useMemo(() => data?.pets ?? [], [data]);
  const [target, setTarget] = useState<string>('owner');
  const [file, setFile] = useState<File | null>(null);
  const [notes, setNotes] = useState('');
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const uploadMutation = useMutation({
    mutationFn: async () => {
      if (!file) {
        throw new Error('Select a file to upload');
      }
      const ownerId = target === 'owner' ? owner?.id : undefined;
      const petId = target !== 'owner' ? target : undefined;
      const presign = await presignDocument({
        filename: file.name,
        contentType: file.type || 'application/octet-stream',
        ownerId,
        petId,
      });
      await uploadDocumentBytes(presign.upload_url, file, presign.headers, token);
      await finalizeDocument({
        uploadRef: presign.upload_ref,
        ownerId,
        petId,
        notes: notes || undefined,
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: PORTAL_ME_QUERY_KEY });
      setFile(null);
      setNotes('');
      setStatus('Document saved.');
      setError(null);
    },
    onError: (uploadError) => {
      setError(uploadError instanceof Error ? uploadError.message : 'Upload failed');
      setStatus(null);
    },
  });

  const handleFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const nextFile = event.target.files?.[0] ?? null;
    setFile(nextFile);
    setStatus(null);
    setError(null);
  };

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!file) {
      setError('Select a file before uploading.');
      return;
    }
    uploadMutation.mutate();
  };

  const documentCards = useMemo(
    () =>
      documents
        .slice()
        .sort((a, b) => (a.created_at < b.created_at ? 1 : -1))
        .map((doc) => ({
          id: doc.id,
          name: doc.file_name,
          url: doc.url_web || doc.url,
          uploadedAt: doc.created_at,
          type: doc.content_type ?? 'document',
        })),
    [documents],
  );

  if (isLoading) {
    return <p className="text-slate-500">Loading documents…</p>;
  }

  return (
    <section className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">Upload a document</h2>
        <p className="text-sm text-slate-500">Share vaccination records, agreements, or notes securely with our team.</p>
        {error && <p className="mt-3 rounded-lg bg-red-50 px-4 py-2 text-sm text-red-600">{error}</p>}
        {status && <p className="mt-3 rounded-lg bg-emerald-50 px-4 py-2 text-sm text-emerald-700">{status}</p>}
        <form className="mt-4 grid gap-4 rounded-2xl bg-white p-6 shadow-sm md:grid-cols-2" onSubmit={handleSubmit}>
          <label className="flex flex-col text-sm font-medium text-slate-700">
            Attach to
            <select
              value={target}
              onChange={(event) => setTarget(event.target.value)}
              className="mt-1 rounded-lg border border-slate-300 px-3 py-2 focus:border-orange-500 focus:outline-none"
            >
              <option value="owner">Owner profile</option>
              {pets.map((pet) => (
                <option key={pet.id} value={pet.id}>
                  {pet.name}
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col text-sm font-medium text-slate-700">
            File
            <input
              type="file"
              onChange={handleFileChange}
              className="mt-1 rounded-lg border border-slate-300 px-3 py-2 focus:border-orange-500 focus:outline-none"
            />
          </label>
          <label className="md:col-span-2 flex flex-col text-sm font-medium text-slate-700">
            Notes
            <textarea
              rows={3}
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              className="mt-1 rounded-lg border border-slate-300 px-3 py-2 focus:border-orange-500 focus:outline-none"
              placeholder="Optional description (e.g., Rabies certificate)"
            />
          </label>
          <button
            type="submit"
            className="md:col-span-2 rounded-lg bg-orange-500 px-4 py-2 font-semibold text-white transition hover:bg-orange-600 disabled:cursor-not-allowed disabled:bg-orange-300"
            disabled={uploadMutation.isPending}
          >
            {uploadMutation.isPending ? 'Uploading…' : 'Upload document'}
          </button>
        </form>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-slate-900">Your documents</h3>
        {documentCards.length === 0 ? (
          <p className="text-sm text-slate-500">No files uploaded yet.</p>
        ) : (
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {documentCards.map((doc) => (
              <a
                key={doc.id}
                className="block rounded-2xl bg-white p-5 shadow-sm transition hover:shadow-md"
                href={doc.url ?? '#'}
                target="_blank"
                rel="noreferrer"
              >
                <p className="text-sm uppercase text-slate-400">{doc.type}</p>
                <p className="mt-2 text-lg font-semibold text-slate-900">{doc.name}</p>
                <p className="mt-1 text-xs text-slate-400">Uploaded {new Date(doc.uploadedAt).toLocaleString()}</p>
              </a>
            ))}
          </div>
        )}
      </div>
    </section>
  );
};

export default Uploads;
