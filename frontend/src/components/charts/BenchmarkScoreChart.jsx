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
      <div>{point.metric}: {point.score.toFixed(3)}</div>
      <div>Mean of {point.foldCount}-fold cross-validation</div>
    </div>
  );
}

// Bar chart comparing real (not simulated) cross-validation scores across
// whichever candidates Person 4 actually benchmarked, so "why this model" has
// a visual side-by-side answer, not just a badge on one card. Sequential blue
// (magnitude), matching every other performance-metric chart in this app.
export default function BenchmarkScoreChart({ recommendations }) {
  const data = (recommendations ?? [])
    .filter((r) => r.benchmark?.status === "completed")
    .map((r) => ({
      name: r.algorithm,
      score: r.benchmark.score,
      metric: r.benchmark.metric,
      foldCount: r.benchmark.cv_scores?.length ?? 5,
    }))
    .sort((a, b) => b.score - a.score);

  if (data.length === 0) return null;
  const height = Math.max(100, data.length * 36);
  const metricLabel = data[0]?.metric ?? "score";

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ left: 8, right: 32, top: 4, bottom: 20 }}>
        <CartesianGrid horizontal={false} stroke={GRIDLINE} />
        <XAxis
          type="number"
          domain={[(dataMin) => Math.min(0, dataMin), 1]}
          tickFormatter={(v) => v.toFixed(1)}
          tick={{ fill: MUTED, fontSize: 11 }}
          axisLine={{ stroke: GRIDLINE }}
          tickLine={false}
          label={{ value: metricLabel, position: "insideBottom", offset: -8, fill: MUTED, fontSize: 11 }}
        />
        <YAxis
          type="category"
          dataKey="name"
          width={170}
          tick={{ fill: MUTED, fontSize: 12 }}
          axisLine={{ stroke: GRIDLINE }}
          tickLine={false}
        />
        <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(0,0,0,0.03)" }} />
        <Bar dataKey="score" fill={SEQUENTIAL_BLUE[400]} radius={[0, 4, 4, 0]} maxBarSize={22} />
      </BarChart>
    </ResponsiveContainer>
  );
}
