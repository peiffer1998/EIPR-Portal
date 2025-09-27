import { useEffect, useState } from "react";

import { fetchDocumentBlob } from "../lib/documentsFetchers";

interface Props {
  id: string;
  onClose: () => void;
}

export default function DocPreview({ id, onClose }: Props) {
  const [url, setUrl] = useState<string | undefined>();
  const [error, setError] = useState<string | undefined>();

  useEffect(() => {
    let active = true;
    let objectUrl: string | null = null;

    setError(undefined);
    setUrl(undefined);

    (async () => {
      try {
        const blob = await fetchDocumentBlob(id);
        objectUrl = URL.createObjectURL(blob);
        if (active) setUrl(objectUrl);
      } catch (err: any) {
        if (active) setError(err?.message || "Preview failed");
      }
    })();

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [id]);

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center">
      <div className="bg-white rounded-xl shadow max-w-[90vw] max-h-[90vh] p-3 grid gap-2">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold">Preview</h3>
          <button type="button" onClick={onClose}>
            Close
          </button>
        </div>
        {error && <div className="text-red-600 text-sm">{error}</div>}
        {url && <iframe src={url} className="w-[80vw] h-[70vh] border rounded" title="Document preview" />}
        {!error && !url && <div className="text-sm text-slate-500">Loading preview…</div>}
      </div>
    </div>
  );
}
