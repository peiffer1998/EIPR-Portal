import { useEffect, useMemo, useRef, useState } from 'react';

import { listOwners, listPets } from '../staff/lib/fetchers';

type QuickSearchProps = {
  open: boolean;
  onClose: () => void;
};

type Result = {
  kind: 'owner' | 'pet';
  id: string;
  label: string;
};

export default function QuickSearch({ open, onClose }: QuickSearchProps): JSX.Element | null {
  const [query, setQuery] = useState('');
  const [owners, setOwners] = useState<any[]>([]);
  const [pets, setPets] = useState<any[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 0);
    } else {
      setQuery('');
      setOwners([]);
      setPets([]);
    }
  }, [open]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (query.trim().length < 2) {
        setOwners([]);
        setPets([]);
        return;
      }
      try {
        const [ownerResults, petResults] = await Promise.all([
          listOwners(query).catch(() => []),
          listPets(undefined, query).catch(() => []),
        ]);
        if (!cancelled) {
          setOwners(ownerResults ?? []);
          setPets(petResults ?? []);
        }
      } catch (error) {
        console.warn('QuickSearch failed', error);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [query]);

  const results = useMemo<Result[]>(
    () => [
      ...owners.map((owner: any) => ({
        kind: 'owner' as const,
        id: owner.id,
        label: `${owner.first_name ?? ''} ${owner.last_name ?? ''} • ${
          owner.email ?? owner.phone ?? owner.id
        }`,
      })),
      ...pets.map((pet: any) => ({
        kind: 'pet' as const,
        id: pet.id,
        label: `${pet.name ?? pet.id} • ${pet.breed ?? pet.species ?? 'Pet'}`,
      })),
    ],
    [owners, pets],
  );

  const handleNavigate = (result: Result) => {
    const href =
      result.kind === 'owner'
        ? `/staff/customers/${result.id}`
        : `/staff/pets/${result.id}`;
    window.location.assign(href);
    onClose();
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[9998] bg-black/40 flex items-start justify-center pt-24">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl p-3 grid gap-2">
        <input
          ref={inputRef}
          className="border rounded px-3 py-2 w-full"
          placeholder="Search owners or pets (type at least 2 chars)"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Escape') {
              event.preventDefault();
              onClose();
            }
          }}
        />
        <div className="max-h-[50vh] overflow-auto">
          {results.length ? (
            results.map((result) => (
              <button
                key={`${result.kind}:${result.id}`}
                type="button"
                className="block w-full text-left px-3 py-2 border-b text-sm hover:bg-slate-50"
                onClick={() => handleNavigate(result)}
              >
                {result.label}
              </button>
            ))
          ) : (
            <div className="px-3 py-6 text-sm text-slate-500">No results</div>
          )}
        </div>
        <div className="text-xs text-slate-500">Enter to open • Esc to close</div>
      </div>
    </div>
  );
}
