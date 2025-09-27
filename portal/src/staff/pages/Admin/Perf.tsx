import { useEffect, useMemo, useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import { aggregate, percentile } from '../../../telemetry/aggregate';

const REFRESH_INTERVAL_MS = 3_000;
const WINDOW_MINUTES = 10;

const vitalConfig = [
  { key: 'LCP', label: 'Largest Contentful Paint (s)', convert: (value: number) => value / 1000 },
  { key: 'CLS', label: 'Cumulative Layout Shift', convert: (value: number) => value },
  { key: 'INP', label: 'Interaction to Next Paint (ms)', convert: (value: number) => value },
  { key: 'FCP', label: 'First Contentful Paint (s)', convert: (value: number) => value / 1000 },
  { key: 'TTFB', label: 'Time to First Byte (ms)', convert: (value: number) => value },
] as const;

type VitalKey = (typeof vitalConfig)[number]['key'];

type VitalCardProps = {
  title: string;
  values: number[];
};

function VitalCard({ title, values }: VitalCardProps) {
  const metrics = useMemo(() => {
    if (!values.length) {
      return { p50: 0, p95: 0, p99: 0, data: [] as Array<{ index: number; value: number }> };
    }

    const p50 = percentile(values, 50);
    const p95 = percentile(values, 95);
    const p99 = percentile(values, 99);
    const data = values.slice(-100).map((value, index) => ({ index, value }));

    return { p50, p95, p99, data };
  }, [values]);

  return (
    <div className="rounded-xl border bg-white p-4 shadow-sm">
      <div className="font-semibold text-slate-900">{title}</div>
      <div className="text-sm text-slate-600">
        p50 {metrics.p50.toFixed(2)} • p95 {metrics.p95.toFixed(2)} • p99 {metrics.p99.toFixed(2)}
      </div>
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={metrics.data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="index" hide />
            <YAxis domain={['dataMin', 'dataMax']} allowDecimals width={48} />
            <Tooltip formatter={(value: number) => value.toFixed(2)} labelFormatter={() => ''} />
            <Line type="monotone" dataKey="value" stroke="#6366f1" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function useAggregation() {
  const [agg, setAgg] = useState(() => aggregate(WINDOW_MINUTES * 60 * 1000));

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const id = window.setInterval(() => {
      setAgg(aggregate(WINDOW_MINUTES * 60 * 1000));
    }, REFRESH_INTERVAL_MS);
    return () => window.clearInterval(id);
  }, []);

  return agg;
}

export default function AdminPerf() {
  const agg = useAggregation();

  const vitalCards = useMemo(() => {
    const cards: Array<{ key: VitalKey; label: string; values: number[] }> = [];
    for (const config of vitalConfig) {
      const bucket = agg.vitals[config.key];
      const values = bucket.map(config.convert);
      cards.push({ key: config.key, label: config.label, values });
    }
    return cards;
  }, [agg.vitals]);

  const latencyData = useMemo(
    () => agg.http.ms.slice(-150).map((value, index) => ({ index, value })),
    [agg.http.ms],
  );

  const codeData = useMemo(
    () => Object.entries(agg.http.codes).map(([code, count]) => ({ code, count })),
    [agg.http.codes],
  );

  return (
    <div className="grid gap-4">
      <div className="rounded-xl border bg-white p-4 shadow-sm">
        <div className="text-sm uppercase tracking-wide text-slate-500">Errors</div>
        <div className={`text-3xl font-semibold ${agg.errors ? 'text-red-600' : 'text-emerald-600'}`}>
          {agg.errors}
        </div>
        <div className="text-xs text-slate-500">Last {WINDOW_MINUTES} minutes</div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {vitalCards.map((card) => (
          <VitalCard key={card.key} title={card.label} values={card.values} />
        ))}
      </div>

      <div className="rounded-xl border bg-white p-4 shadow-sm">
        <div className="font-semibold text-slate-900">HTTP Latency (ms)</div>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={latencyData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="index" hide />
              <YAxis domain={[0, 'dataMax']} width={56} />
              <Tooltip formatter={(value: number) => `${value.toFixed(0)} ms`} labelFormatter={() => ''} />
              <Line type="monotone" dataKey="value" stroke="#10b981" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="rounded-xl border bg-white p-4 shadow-sm">
        <div className="font-semibold text-slate-900">Status Codes</div>
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={codeData} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="code" />
              <YAxis allowDecimals={false} width={48} />
              <Tooltip />
              <Legend />
              <Bar dataKey="count" fill="#6366f1" name="Requests" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
