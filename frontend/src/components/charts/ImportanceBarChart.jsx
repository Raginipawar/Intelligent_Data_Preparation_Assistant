import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { SEQUENTIAL_BLUE } from "./chartColors";

const GRIDLINE = "var(--color-border)";
const MUTED = "var(--color-text-muted)";

function ChartTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const point = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <strong>{point.name}</strong>
      <div>{(point.importance * 100).toFixed(1)}% of gain</div>
    </div>
  );
}

export default function ImportanceBarChart({ importances }) {
  const data = Object.entries(importances ?? {})
    .map(([name, value]) => ({ name, importance: value }))
    .sort((a, b) => b.importance - a.importance);

  if (data.length === 0) return null;
  const height = Math.max(100, data.length * 28);

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24, top: 4, bottom: 4 }}>
        <CartesianGrid horizontal={false} stroke={GRIDLINE} />
        <XAxis
          type="number"
          tickFormatter={(v) => `${Math.round(v * 100)}%`}
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
        <Bar dataKey="importance" fill={SEQUENTIAL_BLUE[400]} radius={[0, 4, 4, 0]} maxBarSize={18} />
      </BarChart>
    </ResponsiveContainer>
  );
}
