// Copyright (c) Ragini Pawar. All rights reserved.
// Original design and source — not to be copied, cloned, or reproduced without permission.
import { Legend, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip } from "recharts";

const MUTED = "var(--color-text-muted)";
const GRIDLINE = "var(--color-border)";
// Categorical series (one hue per algorithm, not a magnitude/polarity encoding),
// so distinct hues are correct here — matches the same accent trio used for the
// BorderGlow cards on the homepage, kept for brand consistency.
const SERIES_COLORS = ["#818cf8", "#38bdf8", "#f472b6", "#facc15", "#34d399"];

function mean(arr) {
  return arr.reduce((a, b) => a + b, 0) / arr.length;
}
function stdDev(arr) {
  if (arr.length < 2) return 0;
  const m = mean(arr);
  return Math.sqrt(mean(arr.map((x) => (x - m) ** 2)));
}
// Min-max normalize to [0, 1] *within the set being compared* — there's no
// natural absolute scale for "how fast" or "how stable" independent of what
// it's being measured against, unlike accuracy which is bounded [0, 1] on its own.
function normalizeRelative(values) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (max === min) return values.map(() => 1);
  return values.map((v) => (v - min) / (max - min));
}

// Multi-axis radar comparing the benchmarked candidates across every REAL,
// measured dimension available — no fabricated axes, no filler numbers:
//   - Recommendation fit: Person 4's meta-learning score (dataset-property match)
//   - Validation accuracy: the actual 5-fold CV score
//   - Speed: inverse fit time, ranked relative to the other benchmarked candidates
//   - Stability: inverse standard deviation across the 5 fold scores, same relative ranking
export default function RadarComparisonChart({ recommendations }) {
  const candidates = (recommendations ?? []).filter((r) => r.benchmark?.status === "completed");
  if (candidates.length === 0) return null;

  const fitTimes = candidates.map((c) => c.benchmark.fit_time_seconds ?? 0);
  const foldStds = candidates.map((c) => stdDev(c.benchmark.cv_scores ?? []));
  const speedScores = normalizeRelative(fitTimes.map((t) => -t));
  const stabilityScores = normalizeRelative(foldStds.map((s) => -s));

  const axes = ["Recommendation fit", "Validation accuracy", "Speed", "Stability"];
  const data = axes.map((axis, axisIndex) => {
    const point = { axis };
    candidates.forEach((c, i) => {
      let value;
      if (axisIndex === 0) value = Math.round((c.recommendation_score ?? 0) * 100);
      else if (axisIndex === 1) value = Math.round(Math.max(0, Math.min(1, c.benchmark.score ?? 0)) * 100);
      else if (axisIndex === 2) value = Math.round(speedScores[i] * 100);
      else value = Math.round(stabilityScores[i] * 100);
      point[c.algorithm] = value;
    });
    return point;
  });

  return (
    <ResponsiveContainer width="100%" height={360}>
      <RadarChart data={data} outerRadius="72%">
        <PolarGrid stroke={GRIDLINE} />
        <PolarAngleAxis dataKey="axis" tick={{ fill: MUTED, fontSize: 12 }} />
        <PolarRadiusAxis angle={90} domain={[0, 100]} tick={{ fill: MUTED, fontSize: 10 }} tickCount={5} />
        {candidates.map((c, i) => (
          <Radar
            key={c.algorithm}
            name={c.algorithm}
            dataKey={c.algorithm}
            stroke={SERIES_COLORS[i % SERIES_COLORS.length]}
            fill={SERIES_COLORS[i % SERIES_COLORS.length]}
            fillOpacity={0.15}
            strokeWidth={2}
          />
        ))}
        <Legend wrapperStyle={{ fontSize: 12, color: MUTED }} />
        <Tooltip
          contentStyle={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: 8,
            fontSize: 12,
            color: "var(--color-text)",
          }}
        />
      </RadarChart>
    </ResponsiveContainer>
  );
}
