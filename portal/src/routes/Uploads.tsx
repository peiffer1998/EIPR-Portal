import { usePortalMe } from '../lib/usePortalMe';

const Uploads = () => {
  const { data, isLoading } = usePortalMe();

  if (isLoading) {
    return <p className="text-slate-500">Loading uploaded documents…</p>;
  }

  const documents = data?.documents ?? [];

  if (documents.length === 0) {
    return (
      <section className="space-y-4">
        <h2 className="text-2xl font-semibold text-slate-900">Documents</h2>
        <p className="text-slate-500">
          Upload vaccination records or agreements and they will appear here. We serve compressed WebP
          previews when available for faster loading.
        </p>
      </section>
    );
  }

  return (
    <section className="space-y-4">
      <h2 className="text-2xl font-semibold text-slate-900">Documents</h2>
      <div className="grid gap-4 md:grid-cols-2">
        {documents.map((doc) => {
          const href = doc.url_web ?? doc.url ?? '#';
          const usesOriginal = !doc.url_web;
          return (
            <a
              key={doc.id}
              className="block rounded-2xl bg-white p-5 shadow-sm transition hover:shadow-md"
              href={href}
              target="_blank"
              rel="noreferrer"
            >
              <p className="text-sm uppercase text-slate-400">
                {doc.content_type ?? 'Document'}
                {usesOriginal ? ' (original)' : ' (optimized)'}
              </p>
              <p className="mt-2 text-lg font-semibold text-slate-900">{doc.file_name}</p>
              <p className="mt-1 text-xs text-slate-400">
                Uploaded {new Date(doc.created_at).toLocaleString()}
              </p>
            </a>
          );
        })}
      </div>
    </section>
  );
};

export default Uploads;
