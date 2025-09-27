import { useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import Page from '../../ui/Page';
import Loading from '../../ui/Loading';
import { Card, CardHeader } from '../../ui/Card';
import Table from '../../ui/Table';
import Button from '../../ui/Button';
import { fmtDateTime } from '../../lib/datetime';
import { toast } from '../../ui/Toast';
import { myDocuments, uploadOwnerFile } from '../lib/fetchers';
import type { OwnerDocument } from '../types';

const OwnerDocuments = (): JSX.Element => {
  const uploadRef = useRef<HTMLInputElement | null>(null);
  const queryClient = useQueryClient();

  const documentsQuery = useQuery({ queryKey: ['owner', 'documents'], queryFn: myDocuments });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadOwnerFile(file),
    onSuccess: (doc) => {
      toast(`Uploaded ${doc.name ?? doc.file_name ?? 'document'}`, 'success');
      queryClient.invalidateQueries({ queryKey: ['owner', 'documents'] });
    },
    onError: () => {
      toast('Upload failed. Please try again.', 'error');
    },
  });

  const handleUpload = () => {
    const file = uploadRef.current?.files?.[0];
    if (!file) return;
    uploadMutation.mutate(file);
    if (uploadRef.current) uploadRef.current.value = '';
  };

  if (documentsQuery.isLoading) {
    return <Loading text="Loading documents…" />;
  }

  if (documentsQuery.isError) {
    return (
      <Page>
        <Page.Header title="Documents" />
        <Card>
          <CardHeader title="Unable to load documents" sub="Please refresh or contact the resort." />
        </Card>
      </Page>
    );
  }

  const documents = documentsQuery.data ?? [];

  return (
    <Page>
      <Page.Header title="Documents" sub="Upload vaccination records or signed waivers." />
      <Card className="p-4">
        <CardHeader title="Upload a document" />
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <input ref={uploadRef} type="file" className="input w-full" />
          <Button
            variant="primary"
            onClick={handleUpload}
            disabled={uploadMutation.isPending}
            type="button"
          >
            {uploadMutation.isPending ? 'Uploading…' : 'Upload'}
          </Button>
        </div>
      </Card>
      <Card className="mt-3 p-0 overflow-hidden">
        <CardHeader title="My documents" sub={`Total: ${documents.length}`} />
        <div className="overflow-x-auto">
          <Table>
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2">Name</th>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {documents.length ? (
                documents.map((doc: OwnerDocument) => (
                  <tr key={doc.id} className="border-t border-slate-100 text-sm">
                    <td className="px-3 py-2">
                      {doc.name ?? doc.file_name ?? 'Document'}
                    </td>
                    <td className="px-3 py-2 text-slate-600">{doc.content_type ?? doc.mime ?? '—'}</td>
                    <td className="px-3 py-2 text-slate-600">
                      {doc.created_at ? fmtDateTime(doc.created_at) : '—'}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={3} className="px-3 py-6 text-center text-sm text-slate-500">
                    No documents on file yet.
                  </td>
                </tr>
              )}
            </tbody>
          </Table>
        </div>
      </Card>
    </Page>
  );
};

export default OwnerDocuments;
