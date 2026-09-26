import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { SEQUENTIAL_BLUE } from "./chartColors";

// Chrome (gridlines/axis text/tooltip) reads the site's theme tokens directly so it
// stays legible in both modes; the data-encoding hue (SEQUENTIAL_BLUE) stays pinned
// to the dataviz skill's validated palette regardless of theme.
const GRIDLINE = "var(--color-border)";
const MUTED = "var(--color-text-muted)";

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{point.name}</strong>
      <div>{point.missing_pct.toFixed(1)}% missing ({point.missing_count} rows)</div>
    </div>
  );
}

export default function MissingnessBarChart({ missingness }) {
  const data = Object.entries(missingness?.columns ?? {})
    .map(([name, info]) => ({ name, missing_pct: info.missing_pct, missing_count: info.missing_count }))
    .filter((d) => d.missing_pct > 0)
    .sort((a, b) => b.missing_pct - a.missing_pct);

  if (data.length === 0) {
    return <p>No missing values detected in any column.</p>;
  }

  const height = Math.max(120, data.length * 32);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke={GRIDLINE} />
        <XAxis
          type="number"
          domain={[0, 100]}
          tickFormatter={(v) => `${v}%`}
          tick={{ fill: MUTED, fontSize: 11 }}
          axisLine={{ stroke: GRIDLINE }}
          tickLine={false}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={140}
          tick={{ fill: MUTED, fontSize: 12 }}
          axisLine={{ stroke: GRIDLINE }}
          tickLine={false}
        />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(0,0,0,0.03)" }} />
        <Bar dataKey="missing_pct" radius={[0, 4, 4, 0]} maxBarSize={18}>
          {data.map((d) => (
            <Cell key={d.name} fill={d.missing_pct >= 50 ? SEQUENTIAL_BLUE[700] : SEQUENTIAL_BLUE[400]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
