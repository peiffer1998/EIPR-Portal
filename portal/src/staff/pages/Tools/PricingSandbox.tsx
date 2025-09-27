import { useCallback, useEffect, useMemo, useState } from "react";

import Button from "../../../ui/Button";
import { Card } from "../../../ui/Card";
import Page from "../../../ui/Page";
import Table from "../../../ui/Table";
import { getQuote, pushRules } from "../../lib/pricingFetchers";
import type { QuoteRequest } from "../../lib/pricingCalc";

const initialForm: QuoteRequest = {
  type: "boarding",
  nights: 1,
  lodging: "room",
  dogs: 1,
  daycare_with_boarding: false,
  fees: { early: false, late: false, flea: false },
  use_daycare_package: false,
};

type QuoteState = Awaited<ReturnType<typeof getQuote>> | null;

type Status = "idle" | "loading" | "ready";

type PushState = "" | "success" | "noop";

const currency = (value: number) => `$${Number(value).toFixed(2)}`;

function exportCsv(quote: QuoteState) {
  if (!quote) return;
  const rows = [
    ["Label", "Quantity", "Unit", "Unit Price", "Amount"],
    ...quote.lines.map((line) => [
      line.label,
      String(line.qty),
      line.unit,
      Number(line.unit_price).toFixed(2),
      Number(line.amount).toFixed(2),
    ]),
    ["Subtotal", "", "", "", Number(quote.subtotal).toFixed(2)],
    ["Discounts", "", "", "", (-Number(quote.discount_total)).toFixed(2)],
    ["Total", "", "", "", Number(quote.total).toFixed(2)],
  ];
  const csv = rows.map((row) => row.map((cell) => `"${cell.replaceAll('"', '""')}"`).join(",")).join("\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `pricing-quote-${Date.now()}.csv`;
  anchor.click();
  URL.revokeObjectURL(url);
}

export default function PricingSandbox(): JSX.Element {
  const [form, setForm] = useState<QuoteRequest>(initialForm);
  const [quote, setQuote] = useState<QuoteState>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [pushStatus, setPushStatus] = useState<PushState>("");

  const runQuote = useCallback(async (input: QuoteRequest) => {
    setStatus("loading");
    try {
      const result = await getQuote(input);
      setQuote(result);
      setStatus("ready");
    } catch (err) {
      console.error("Quote failed", err);
      setQuote(null);
      setStatus("idle");
    }
  }, []);

  useEffect(() => {
    void runQuote(form);
  }, [form, runQuote]);

  const onInputChange = useCallback(<K extends keyof QuoteRequest>(key: K, value: QuoteRequest[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  }, []);

  const fees = useMemo(() => form.fees ?? { early: false, late: false, flea: false }, [form.fees]);

  async function handlePushRules() {
    const result = await pushRules();
    setPushStatus(result.pushed ? "success" : "noop");
    setTimeout(() => setPushStatus(""), 4_000);
  }

  return (
    <Page>
      <Page.Header
        title="Pricing Sandbox"
        sub="Run what-if scenarios for daycare and boarding quotes."
        actions={
          <>
            <Button variant="ghost" onClick={() => exportCsv(quote)}>Export CSV</Button>
            <Button variant="primary" onClick={handlePushRules}>Push rules</Button>
          </>
        }
      />

      <Card className="p-4">
        <div className="grid gap-3 md:grid-cols-4">
          <label className="text-sm grid">
            <span>Reservation type</span>
            <select
              className="select"
              value={form.type}
              onChange={(event) => onInputChange("type", event.target.value as QuoteRequest["type"])}
            >
              <option value="boarding">Boarding</option>
              <option value="daycare">Daycare</option>
            </select>
          </label>

          {form.type === "boarding" && (
            <>
              <label className="text-sm grid">
                <span>Nights</span>
                <input
                  className="input"
                  type="number"
                  min={1}
                  value={form.nights ?? 1}
                  onChange={(event) => onInputChange("nights", Math.max(1, Number(event.target.value) || 1))}
                />
              </label>
              <label className="text-sm grid">
                <span>Lodging</span>
                <select
                  className="select"
                  value={form.lodging ?? "room"}
                  onChange={(event) => onInputChange("lodging", event.target.value as QuoteRequest["lodging"])}
                >
                  <option value="room">Room</option>
                  <option value="suite">Suite</option>
                </select>
              </label>
              <label className="text-sm grid">
                <span>Dogs</span>
                <select
                  className="select"
                  value={form.dogs ?? 1}
                  onChange={(event) => onInputChange("dogs", Number(event.target.value) as 1 | 2 | 3)}
                >
                  <option value={1}>1</option>
                  <option value={2}>2</option>
                  <option value={3}>3</option>
                </select>
              </label>
              <label className="text-sm grid gap-1">
                <span>Daycare with boarding</span>
                <input
                  type="checkbox"
                  checked={!!form.daycare_with_boarding}
                  onChange={(event) => onInputChange("daycare_with_boarding", event.target.checked)}
                />
              </label>
              <label className="text-sm grid gap-1">
                <span>Early drop-off</span>
                <input
                  type="checkbox"
                  checked={!!fees.early}
                  onChange={(event) => onInputChange("fees", { ...fees, early: event.target.checked })}
                />
              </label>
              <label className="text-sm grid gap-1">
                <span>Late pick-up</span>
                <input
                  type="checkbox"
                  checked={!!fees.late}
                  onChange={(event) => onInputChange("fees", { ...fees, late: event.target.checked })}
                />
              </label>
              <label className="text-sm grid gap-1">
                <span>Flea treatment</span>
                <input
                  type="checkbox"
                  checked={!!fees.flea}
                  onChange={(event) => onInputChange("fees", { ...fees, flea: event.target.checked })}
                />
              </label>
            </>
          )}

          {form.type === "daycare" && (
            <>
              <label className="text-sm grid">
                <span>Days</span>
                <input
                  className="input"
                  type="number"
                  min={1}
                  value={form.days ?? 1}
                  onChange={(event) => onInputChange("days", Math.max(1, Number(event.target.value) || 1))}
                />
              </label>
              <label className="text-sm grid gap-1">
                <span>Use package credits</span>
                <input
                  type="checkbox"
                  checked={!!form.use_daycare_package}
                  onChange={(event) => onInputChange("use_daycare_package", event.target.checked)}
                />
              </label>
            </>
          )}
        </div>
        <div className="mt-3 text-sm text-slate-500">
          Status: {status === "loading" ? "Calculating…" : status === "ready" ? "Ready" : "Idle"}
          {pushStatus === "success" && <span className="ml-2 text-green-600">Rules pushed to /pricing/rules</span>}
          {pushStatus === "noop" && <span className="ml-2 text-slate-500">Rules endpoint unavailable (using local policy)</span>}
        </div>
      </Card>

      {quote && (
        <Card className="p-0 overflow-hidden">
          <div className="px-4 py-3 font-semibold border-b border-slate-100">Quote preview</div>
          <div className="overflow-auto">
            <Table>
              <thead>
                <tr className="text-left text-slate-500">
                  <th className="px-3 py-2">Line</th>
                  <th>Qty</th>
                  <th>Unit</th>
                  <th>Unit price</th>
                  <th>Amount</th>
                </tr>
              </thead>
              <tbody>
                {quote.lines.map((line, index) => (
                  <tr key={`${line.label}-${index}`} className="border-t border-slate-100">
                    <td className="px-3 py-2">{line.label}</td>
                    <td>{line.qty}</td>
                    <td>{line.unit}</td>
                    <td>{currency(line.unit_price)}</td>
                    <td>{currency(line.amount)}</td>
                  </tr>
                ))}
                <tr className="border-t border-slate-200 font-semibold">
                  <td className="px-3 py-2" colSpan={4}>Subtotal</td>
                  <td>{currency(quote.subtotal)}</td>
                </tr>
                <tr className="font-semibold">
                  <td className="px-3 py-2" colSpan={4}>Discounts</td>
                  <td>-{currency(quote.discount_total)}</td>
                </tr>
                <tr className="font-semibold text-lg">
                  <td className="px-3 py-2" colSpan={4}>Total</td>
                  <td>{currency(quote.total)}</td>
                </tr>
              </tbody>
            </Table>
          </div>
        </Card>
      )}
    </Page>
  );
}
