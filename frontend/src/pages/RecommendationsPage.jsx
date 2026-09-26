// Copyright (c) Ragini Pawar. All rights reserved.
// Original design and source — not to be copied, cloned, or reproduced without permission.
import { useNavigate } from "react-router-dom";
import { usePipeline } from "../context/PipelineContext";
import { isPerson4Mocked } from "../api/person4Api";
import { stripLongDashes } from "../utils/text";

const SUITABILITY_BADGE = {
  high: "badge-success",
  medium: "badge-warning",
  low: "badge-neutral",
};

const METRIC_LABEL = {
  accuracy: "Accuracy",
  f1_macro: "F1 (macro)",
  r2: "R²",
};

// Step 6 — purely a display of what step 5 (ValidationAccuracyPage) already
// fetched into PipelineContext. No API call happens here; if recommendations
// aren't loaded yet, this sends the user back to Validation, which owns the
// single /recommend request for both steps.
export default function RecommendationsPage() {
  const pipeline = usePipeline();
  const navigate = useNavigate();

  if (!pipeline.applyResult) {
    return (
      <div className="card">
        <p>Apply your suggestions first to get algorithm recommendations.</p>
        <button className="btn btn-secondary" onClick={() => navigate("/workspace/apply")} style={{ marginTop: 12 }}>
          ← Back to Apply
        </button>
      </div>
    );
  }

  if (!pipeline.recommendations) {
    return (
      <div className="card">
        <p>Run validation first to see algorithm recommendations backed by real accuracy scores.</p>
        <button className="btn btn-secondary" onClick={() => navigate("/workspace/validation")} style={{ marginTop: 12 }}>
          ← Back to Validation &amp; Accuracy
        </button>
      </div>
    );
  }

  const recs = pipeline.recommendations;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div className="page-header">
        <h1>Recommended algorithms</h1>
        <p>Ranked candidates for your cleaned dataset, with reasoning and, where benchmarked, real cross-validation scores.</p>
      </div>

      {isPerson4Mocked && (
        <div className="mock-banner">
          Person 4's recommendation engine is running in mock mode (VITE_MOCK_PERSON4=true).
        </div>
      )}

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
        <span className="badge badge-primary">{recs.task_type}</span>
        {recs.target_column && <span className="badge badge-neutral">target: {recs.target_column}</span>}
        {!recs.benchmarked && <span className="badge badge-warning">not benchmarked</span>}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {recs.recommendations.map((rec) => (
          <div key={rec.algorithm} className="card" style={{ display: "flex", gap: 16, alignItems: "flex-start" }}>
            <span className="badge badge-neutral" style={{ flexShrink: 0 }}>#{rec.rank}</span>
            <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
                <h3>{rec.algorithm}</h3>
                <div style={{ display: "flex", gap: 6 }}>
                  <span className={`badge ${SUITABILITY_BADGE[rec.suitability] ?? "badge-neutral"}`}>{rec.suitability}</span>
                  {rec.benchmark?.status === "completed" && (
                    <span className="badge badge-success">
                      {METRIC_LABEL[rec.benchmark.metric] ?? rec.benchmark.metric} {rec.benchmark.score?.toFixed(3)}
                    </span>
                  )}
                </div>
              </div>
              <ul style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 4 }}>
                {rec.reasoning.map((line, i) => (
                  <li key={i} style={{ fontSize: 13.5, color: "var(--color-text-muted)" }}>
                    {stripLongDashes(line)}
                  </li>
                ))}
              </ul>
              {rec.benchmark?.status === "completed" ? (
                <span className="mono" style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                  cv scores: [{rec.benchmark.cv_scores?.map((s) => s.toFixed(2)).join(", ")}] · fit {rec.benchmark.fit_time_seconds?.toFixed(2)}s
                </span>
              ) : (
                <span style={{ fontSize: 12, color: "var(--color-text-muted)" }}>
                  {rec.benchmark?.note
                    ? stripLongDashes(rec.benchmark.note)
                    : `Not in the top ${recs.recommendations.filter((r) => r.benchmark?.status === "completed").length} benchmarked candidates. Score is meta-learning only.`}
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 12 }}>
        <button className="btn btn-secondary" onClick={() => navigate("/workspace/validation")}>
          ← Back to Validation &amp; Accuracy
        </button>
        <button className="btn btn-secondary" onClick={() => { pipeline.reset(); navigate("/workspace"); }}>
          Start a new dataset
        </button>
      </div>
    </div>
  );
}
