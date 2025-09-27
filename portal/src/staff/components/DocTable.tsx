import CopyButton from "./CopyButton";
import { buildDocumentLink } from "../lib/documentsFetchers";

interface Props {
  rows: Array<any>;
  onPreview: (id: string) => void;
  onFinalize: (id: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}

const formatSize = (size?: number | null) => {
  if (size === undefined || size === null) return "";
  if (size < 1024) return `${size} B`;
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`;
  return `${(size / (1024 * 1024)).toFixed(1)} MB`;
};

export default function DocTable({ rows, onPreview, onFinalize, onDelete }: Props) {
  return (
    <div className="bg-white rounded-xl shadow overflow-auto">
      <table className="w-full text-sm">
        <thead className="sticky top-0 bg-white border-b">
          <tr className="text-left text-slate-500">
            <th className="px-3 py-2">Name</th>
            <th>Type</th>
            <th>Size</th>
            <th>Owner</th>
            <th>Pet</th>
            <th>Status</th>
            <th>Uploaded</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {(rows || []).map((doc: any) => (
            <tr key={doc.id} className="border-t">
              <td className="px-3 py-2">{doc.name || doc.key || doc.id}</td>
              <td>{doc.mime || doc.content_type || ""}</td>
              <td>{formatSize(doc.size_bytes ?? doc.size)}</td>
              <td>{doc.owner_id || ""}</td>
              <td>{doc.pet_id || ""}</td>
              <td>{(doc.status || "uploaded").toUpperCase()}</td>
              <td>{doc.created_at ? String(doc.created_at).slice(0, 16).replace("T", " ") : ""}</td>
              <td className="py-2">
                <div className="flex gap-2">
                  <button className="px-2 py-1 rounded border text-xs" type="button" onClick={() => onPreview(doc.id)}>
                    Preview
                  </button>
                  <button
                    className="px-2 py-1 rounded border text-xs"
                    type="button"
                    onClick={() => onFinalize(doc.id)}
                  >
                    Finalize
                  </button>
                  <CopyButton text={buildDocumentLink(doc.id)} />
                  <button
                    className="px-2 py-1 rounded border text-xs text-red-600"
                    type="button"
                    onClick={() => onDelete(doc.id)}
                  >
                    Delete
                  </button>
                </div>
              </td>
            </tr>
          ))}
          {(!rows || rows.length === 0) && (
            <tr>
              <td colSpan={8} className="px-3 py-4 text-sm text-slate-500">
                No documents
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
