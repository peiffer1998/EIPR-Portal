import { useState } from "react";

import Button from "../../../ui/Button";
import { Card } from "../../../ui/Card";
import Page from "../../../ui/Page";
import { Input, Label } from "../../../ui/Inputs";
import { downloadCsv } from "../../lib/staffApi";
import { P } from "../../lib/paths";

export default function Reports() {
  const [from, setFrom] = useState(new Date(Date.now() - 7 * 864e5).toISOString().slice(0, 10));
  const [to, setTo] = useState(new Date().toISOString().slice(0, 10));

  const btn = (label: string, path: string) => (
    <Button
      key={label}
      type="button"
      onClick={() => downloadCsv(path, `${label}_${from}_${to}.csv`)}
    >
      {label}
    </Button>
  );

  return (
    <Page>
      <Page.Header title="Reports" sub="Download operational exports" />

      <Card className="max-w-2xl">
        <div className="grid gap-3">
          <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
            <Label>
              <span>From</span>
              <Input type="date" value={from} onChange={(event) => setFrom(event.target.value)} />
            </Label>
            <Label>
              <span>To</span>
              <Input type="date" value={to} onChange={(event) => setTo(event.target.value)} />
            </Label>
          </div>

          <div className="grid gap-2 md:grid-cols-2">
            {btn("Revenue", P.reportsMax.revenue(from, to))}
            {btn("Occupancy", P.reportsMax.occupancy(from, to))}
            {btn("Payments", P.reportsMax.payments(from, to))}
            {btn("Deposits", P.reportsMax.deposits(from, to))}
            {btn("Commissions", P.reportsMax.commissions(from, to))}
            {btn("Tips", P.reportsMax.tips(from, to))}
          </div>
        </div>
      </Card>
    </Page>
  );
}
