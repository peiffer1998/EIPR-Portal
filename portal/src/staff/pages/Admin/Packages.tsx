import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import ActiveToggle from "../../components/ActiveToggle";
import DrawerForm from "../../components/DrawerForm";
import Money from "../../components/Money";
import SearchBox from "../../components/SearchBox";
import {
  createPackageDef,
  deletePackageDef,
  listPackageDefs,
  listServiceItems,
  updatePackageDef,
} from "../../lib/catalogFetchers";

type Row = {
  id: string;
  name: string;
  credits: number;
  credit_unit: string;
  price: number;
  active: boolean;
  reservation_type?: string;
  service_item_id?: string;
};

export default function AdminPackages() {
  const queryClient = useQueryClient();
  const [search, setSearch] = useState("");
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editing, setEditing] = useState<Row | null>(null);

  const packagesQuery = useQuery({
    queryKey: ["package-defs"],
    queryFn: () => listPackageDefs({ limit: 500 }),
  });
  const servicesQuery = useQuery({
    queryKey: ["services"],
    queryFn: () => listServiceItems({ limit: 500 }),
  });

  const serviceOptions = useMemo(
    () =>
      (servicesQuery.data || []).map((service: any) => ({
        value: String(service.id),
        label: service.name || service.title || String(service.id),
      })),
    [servicesQuery.data],
  );

  const rows = useMemo<Row[]>(() => {
    const mapped = (packagesQuery.data || []).map((pkg: any) => ({
      id: String(pkg.id),
      name: pkg.name || "",
      credits: Number(pkg.credits ?? pkg.quantity ?? 0),
      credit_unit: pkg.credit_unit || "unit",
      price: Number(pkg.price ?? 0),
      active: pkg.active !== false,
      reservation_type: pkg.reservation_type || undefined,
      service_item_id: pkg.service_item_id || undefined,
    }));
    if (!search) return mapped;
    const normalized = search.toLowerCase();
    return mapped.filter((row) => row.name.toLowerCase().includes(normalized));
  }, [packagesQuery.data, search]);

  const createMutation = useMutation({
    mutationFn: (values: Record<string, any>) =>
      createPackageDef({
        name: values.name,
        credits: Number(values.credits || 0),
        credit_unit: values.credit_unit || "unit",
        price: Number(values.price || 0),
        active: Boolean(values.active),
        reservation_type: values.reservation_type || undefined,
        service_item_id: values.service_item_id || undefined,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["package-defs"] }),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Record<string, any> }) =>
      updatePackageDef(id, patch),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["package-defs"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => deletePackageDef(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["package-defs"] }),
  });

  return (
    <div className="grid gap-3">
      <div className="bg-white p-3 rounded-xl shadow flex items-center justify-between">
        <SearchBox onChange={setSearch} placeholder="Search packages" />
        <button
          className="px-3 py-2 rounded bg-slate-900 text-white"
          type="button"
          onClick={() => {
            setEditing(null);
            setDrawerOpen(true);
          }}
        >
          New Package
        </button>
      </div>

      <div className="bg-white rounded-xl shadow overflow-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 bg-white border-b">
            <tr className="text-left text-slate-500">
              <th className="px-3 py-2">Name</th>
              <th>Credits</th>
              <th>Price</th>
              <th>Applied To</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.id} className="border-t">
                <td className="px-3 py-2">{row.name}</td>
                <td>
                  {row.credits} {row.credit_unit}
                </td>
                <td>
                  <Money value={row.price} />
                </td>
                <td>
                  {row.service_item_id
                    ? `Service #${row.service_item_id}`
                    : (row.reservation_type || "Any").toUpperCase()}
                </td>
                <td>
                  <ActiveToggle
                    value={row.active}
                    onChange={(value) =>
                      updateMutation.mutateAsync({
                        id: row.id,
                        patch: { active: value },
                      })
                    }
                  />
                </td>
                <td className="py-2">
                  <div className="flex gap-2">
                    <button
                      className="text-xs border px-2 py-1 rounded"
                      type="button"
                      onClick={() => {
                        setEditing(row);
                        setDrawerOpen(true);
                      }}
                    >
                      Edit
                    </button>
                    <button
                      className="text-xs text-red-600 px-2 py-1"
                      type="button"
                      onClick={() => deleteMutation.mutate(row.id)}
                    >
                      Archive
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {rows.length === 0 && !packagesQuery.isFetching && (
              <tr>
                <td colSpan={6} className="px-3 py-4 text-sm text-slate-500">
                  No packages
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <DrawerForm
        title={editing ? "Edit Package" : "New Package"}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        initial={
          editing || {
            active: true,
            credits: 0,
            credit_unit: "unit",
            price: 0,
            reservation_type: "",
          }
        }
        fields={[
          { name: "name", label: "Name" },
          { name: "credits", label: "Credits", type: "number", placeholder: "10" },
          { name: "credit_unit", label: "Credit Unit", type: "text", placeholder: "day, session, unit" },
          { name: "price", label: "Price", type: "number", placeholder: "0.00" },
          {
            name: "reservation_type",
            label: "Reservation Type",
            type: "select",
            options: [
              { value: "", label: "Any" },
              { value: "boarding", label: "BOARDING" },
              { value: "daycare", label: "DAYCARE" },
              { value: "grooming", label: "GROOMING" },
            ],
          },
          {
            name: "service_item_id",
            label: "Service Item (optional)",
            type: "select",
            options: serviceOptions,
          },
          { name: "active", label: "Active", type: "checkbox" },
        ]}
        onSubmit={async (values) => {
          const payload = {
            name: values.name,
            credits: Number(values.credits || 0),
            credit_unit: values.credit_unit || "unit",
            price: Number(values.price || 0),
            active: Boolean(values.active),
            reservation_type: values.reservation_type || undefined,
            service_item_id: values.service_item_id || undefined,
          };

          if (editing) {
            await updateMutation.mutateAsync({ id: editing.id, patch: payload });
          } else {
            await createMutation.mutateAsync(payload);
          }

          setDrawerOpen(false);
        }}
      />
    </div>
  );
}
