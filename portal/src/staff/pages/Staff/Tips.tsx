import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { createTip, listTips } from "../../lib/fetchers";

export default function Tips() {
  const tips = useQuery({ queryKey: ["tips"], queryFn: () => listTips() });
  const [loc, setLoc] = useState(localStorage.getItem("defaultLocationId") || "");
  const [amount, setAmount] = useState("20.00");
  const [user, setUser] = useState("");

  const record = async () => {
    await createTip({
      location_id: loc,
      date: new Date().toISOString().slice(0, 10),
      amount,
      policy: "direct_to_staff",
      recipients: [[user, amount]],
    });
    await tips.refetch();
    alert("Tip recorded");
  };

  return (
    <div className="bg-white p-6 rounded-xl shadow">
      <h3 className="text-xl font-semibold">Tips</h3>
      <div className="flex gap-2 mb-3">
        <input
          className="border rounded px-3 py-2"
          placeholder="Location UUID"
          value={loc}
          onChange={(event) => setLoc(event.target.value)}
        />
        <input
          className="border rounded px-3 py-2"
          placeholder="Recipient User UUID"
          value={user}
          onChange={(event) => setUser(event.target.value)}
        />
        <input
          className="border rounded px-3 py-2"
          value={amount}
          onChange={(event) => setAmount(event.target.value)}
        />
        <button className="bg-slate-900 text-white px-3 py-2 rounded" onClick={record} type="button">
          Record
        </button>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-slate-500">
            <th>Date</th>
            <th>Policy</th>
            <th>Amount</th>
          </tr>
        </thead>
        <tbody>
          {(tips.data || []).map((t: any) => (
            <tr key={t.id} className="border-t">
              <td className="py-2">{t.date}</td>
              <td>{t.policy}</td>
              <td>{t.amount}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
