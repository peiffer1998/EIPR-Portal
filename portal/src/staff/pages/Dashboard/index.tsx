import { useQuery } from "@tanstack/react-query";

import Page from "../../../ui/Page";
import { jsonRevenue, jsonOccupancy } from "../../lib/fetchers";

const today = new Date().toISOString().slice(0, 10);

export default function StaffDashboard() {
  const occ = useQuery({ queryKey: ["occ", today], queryFn: () => jsonOccupancy(today, today) });
  const rev = useQuery({ queryKey: ["rev", today], queryFn: () => jsonRevenue(today, today) });
  const booked = (Array.isArray(occ.data) && occ.data[0]?.booked) || 0;
  const total = typeof rev.data?.total === "number" ? rev.data.total : 0;

  return (
    <Page>
      <Page.Header title="Dashboard" sub="Today at a glance" />

      <div className="grid gap-4 md:grid-cols-3">
        <div className="rounded-xl bg-white p-5 shadow">
          <p className="text-xs uppercase text-slate-500">Today occupancy</p>
          <p className="text-3xl font-semibold">{booked}</p>
        </div>
        <div className="rounded-xl bg-white p-5 shadow">
          <p className="text-xs uppercase text-slate-500">Revenue window</p>
          <p className="text-3xl font-semibold">${total}</p>
        </div>
        <div className="rounded-xl bg-white p-5 shadow">
          <p className="text-xs uppercase text-slate-500">Quick start</p>
          <ul className="list-disc pl-5 text-sm">
            <li>
              <a className="text-blue-700" href="/staff/reservations/new">
                Create reservation
              </a>
            </li>
            <li>
              <a className="text-blue-700" href="/staff/grooming/new">
                Create grooming appt
              </a>
            </li>
            <li>
              <a className="text-blue-700" href="/staff/reports">
                Open reports
              </a>
            </li>
          </ul>
        </div>
      </div>
    </Page>
  );
}
