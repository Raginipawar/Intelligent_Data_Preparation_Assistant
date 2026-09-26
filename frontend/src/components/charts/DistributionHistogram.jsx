import { Bar, BarChart, ResponsiveContainer, Tooltip } from "recharts";
import { SEQUENTIAL_BLUE } from "./chartColors";

function binLabel(edges, i) {
  const lo = edges[i];
  const hi = edges[i + 1];
  const fmt = (n) => (Math.abs(n) >= 1000 ? n.toFixed(0) : n.toFixed(1));
  return `${fmt(lo)}–${fmt(hi)}`;
}

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <div>{point.label}</div>
      <strong>{point.count} rows</strong>
    </div>
  );
}

export default function DistributionHistogram({ column, dist }) {
  const edges = dist.histogram?.bin_edges ?? [];
  const counts = dist.histogram?.counts ?? [];
  const data = counts.map((count, i) => ({ label: binLabel(edges, i), count }));

  const skew = dist.skewness;
  const skewBadge =
    skew == null ? null : Math.abs(skew) >= 1 ? "badge-warning" : "badge-neutral";

  return (
    <div className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <strong style={{ fontSize: 13.5 }}>{column}</strong>
        {skew != null && <span className={`badge ${skewBadge}`}>skew {skew.toFixed(2)}</span>}
      </div>
      <ResponsiveContainer width="100%" height={80}>
        <BarChart data={data} margin={{ top: 2, right: 2, left: 2, bottom: 2 }}>
          <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(0,0,0,0.03)" }} />
          <Bar dataKey="count" fill={SEQUENTIAL_BLUE[400]} radius={[2, 2, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--color-text-muted)" }}>
        <span>mean {dist.mean?.toFixed(2)}</span>
        <span>median {dist.median?.toFixed(2)}</span>
        <span>std {dist.std?.toFixed(2)}</span>
      </div>
    </div>
  );
}
