import { useCallback, useRef, type FocusEvent } from 'react';
import { useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import Page from '../../../ui/Page';
import Loading from '../../../ui/Loading';
import { Card, CardHeader } from '../../../ui/Card';
import Button from '../../../ui/Button';
import { toast } from '../../../ui/Toast';
import { fmtDate } from '../../../lib/datetime';
import { petDetail, updatePet, uploadPetFile } from '../../lib/fetchers';
import type { OwnerPet, OwnerPetFile } from '../../types';

const OwnerPetDetail = (): JSX.Element => {
  const { petId } = useParams<{ petId: string }>();
  const queryClient = useQueryClient();
  const uploadRef = useRef<HTMLInputElement | null>(null);

  const petQuery = useQuery({
    queryKey: ['owner', 'pet', petId],
    queryFn: () => petDetail(petId ?? ''),
    enabled: Boolean(petId),
  });

  const updateMutation = useMutation({
    mutationFn: (payload: Partial<OwnerPet>) => updatePet(petId ?? '', payload),
    onSuccess: (next) => {
      queryClient.setQueryData(['owner', 'pet', petId], next);
      queryClient.invalidateQueries({ queryKey: ['owner', 'pets'] });
      toast('Pet updated', 'success');
    },
  });

  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadPetFile(petId ?? '', file),
    onSuccess: (file: OwnerPetFile) => {
      toast(`Uploaded ${file.name ?? file.file_name ?? 'document'}`, 'success');
      queryClient.invalidateQueries({ queryKey: ['owner', 'pet', petId] });
    },
  });

  const pet = petQuery.data;

  const handleFieldBlur = useCallback(
    (field: keyof OwnerPet) => (event: FocusEvent<HTMLInputElement>) => {
      if (!petId) return;
      const value = event.target.value;
      updateMutation.mutate({ [field]: value || null } as Partial<OwnerPet>);
    },
    [petId, updateMutation],
  );

  const handleFileUpload = useCallback(async () => {
    if (!uploadRef.current?.files?.length) return;
    const file = uploadRef.current.files[0];
    if (!file) return;
    uploadMutation.mutate(file);
    uploadRef.current.value = '';
  }, [uploadMutation]);

  if (petQuery.isLoading || !petId) {
    return <Loading text="Loading pet details…" />;
  }

  if (petQuery.isError || !pet) {
    return (
      <Page>
        <Page.Header title="Pet details" />
        <Card>
          <CardHeader title="Pet not found" sub="We could not load this pet." />
        </Card>
      </Page>
    );
  }

  const documents = (pet.files ?? []) as OwnerPetFile[];

  return (
    <Page>
      <Page.Header title={pet.name ?? 'Pet details'} sub="Update info and upload documents" />
      <Card className="p-4">
        <CardHeader title="Profile" />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <label className="text-sm font-medium text-slate-600">
            Name
            <input
              className="input mt-1 w-full"
              defaultValue={pet.name ?? ''}
              onBlur={handleFieldBlur('name')}
              placeholder="Pet name"
            />
          </label>
          <label className="text-sm font-medium text-slate-600">
            Breed
            <input
              className="input mt-1 w-full"
              defaultValue={pet.breed ?? ''}
              onBlur={handleFieldBlur('breed')}
              placeholder="Breed"
            />
          </label>
          <label className="text-sm font-medium text-slate-600">
            Species
            <input
              className="input mt-1 w-full"
              defaultValue={pet.species ?? ''}
              onBlur={handleFieldBlur('species')}
              placeholder="Species"
            />
          </label>
          <label className="text-sm font-medium text-slate-600">
            Birthdate
            <input
              className="input mt-1 w-full"
              type="date"
              defaultValue={pet.birthdate ?? ''}
              onBlur={handleFieldBlur('birthdate')}
            />
          </label>
        </div>
      </Card>
      <Card className="p-4">
        <CardHeader title="Documents" sub="Vaccination records and attachments" />
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
          <input ref={uploadRef} type="file" className="input w-full" />
          <Button
            variant="primary"
            onClick={handleFileUpload}
            disabled={uploadMutation.isPending}
            type="button"
          >
            {uploadMutation.isPending ? 'Uploading…' : 'Upload'}
          </Button>
        </div>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-sm table-sticky">
            <thead>
              <tr className="text-left text-xs uppercase tracking-wide text-slate-500">
                <th className="px-3 py-2">File</th>
                <th className="px-3 py-2">Type</th>
                <th className="px-3 py-2">Uploaded</th>
              </tr>
            </thead>
            <tbody>
              {documents.length ? (
                documents.map((doc) => (
                  <tr key={doc.id} className="border-t border-slate-100">
                    <td className="px-3 py-2 text-sm text-slate-800">{doc.name ?? doc.file_name ?? 'Document'}</td>
                    <td className="px-3 py-2 text-sm text-slate-600">{doc.content_type ?? doc.mime ?? '—'}</td>
                    <td className="px-3 py-2 text-sm text-slate-600">
                      {doc.created_at ? fmtDate(doc.created_at) : '—'}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={3} className="px-3 py-6 text-center text-sm text-slate-500">
                    No documents uploaded yet. Upload vaccination records or other files above.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </Page>
  );
};

export default OwnerPetDetail;
