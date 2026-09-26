// Copyright (c) Ragini Pawar. All rights reserved.
// Original design and source — not to be copied, cloned, or reproduced without permission.
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePipeline } from "../context/PipelineContext";
import { recommendAndWait, isPerson4Mocked } from "../api/person4Api";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorBanner from "../components/ErrorBanner";
import BenchmarkScoreChart from "../components/charts/BenchmarkScoreChart";
import RadarComparisonChart from "../components/charts/RadarComparisonChart";
import { stripLongDashes } from "../utils/text";

const METRIC_LABEL = {
  accuracy: "Accuracy",
  f1_macro: "F1 (macro)",
  r2: "R²",
};

// Distinct labeling per real backend status, not a single generic "not
// benchmarked" — a candidate that was attempted and failed, one that was
// deliberately skipped (e.g. single-class target), and one never attempted
// because it was outside top_k_benchmark are three different situations, and
// collapsing them was exactly what made a previous run's all-N/A table look
// like nothing had run at all when several candidates had actually failed.
const STATUS_BADGE = {
  completed: { label: "Empirically validated (5-fold CV)", cls: "badge-success" },
  failed: { label: "Benchmark failed", cls: "badge-danger" },
  skipped: { label: "Skipped", cls: "badge-warning" },
  none: { label: "Not benchmarked", cls: "badge-neutral" },
};

const REFERENCES = [
  {
    text: "Rice, J. R. (1976). “The Algorithm Selection Problem.” Advances in Computers, Vol. 15.",
    note: "The foundational formalization of matching algorithms to problem characteristics, the same idea behind the meta-learning fit score above.",
  },
  {
    text: "Stone, M. (1974). “Cross-Validatory Choice and Assessment of Statistical Predictions.” Journal of the Royal Statistical Society, Series B.",
    note: "The classical statistical basis for k-fold cross-validation, the method used for the empirical benchmark scores above.",
  },
  {
    text: "scikit-learn: Cross-validation, evaluating estimator performance",
    href: "https://scikit-learn.org/stable/modules/cross_validation.html",
    note: "The library and exact methodology (StratifiedKFold / KFold + cross_val_score) used to compute the scores above.",
  },
  {
    text: "He, X., Zhao, K., & Chu, X. (2021). “AutoML: A Survey of the State-of-the-Art.” Knowledge-Based Systems.",
    href: "https://arxiv.org/pdf/1908.00709",
    note: "Broader survey covering meta-learning-based algorithm/model selection within AutoML pipelines.",
  },
];

// This page owns the single /recommend call — it's step 5, the first of the two
// steps that need Person 4's data (step 6, RecommendationsPage, just reads the
// result back out of PipelineContext). Both the validation evidence here and the
// ranked algorithm list there come from that one API response.
export default function ValidationAccuracyPage() {
  const pipeline = usePipeline();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [statusText, setStatusText] = useState(null);
  const startedForRef = useRef(null);

  useEffect(() => {
    if (!pipeline.applyResult || pipeline.recommendations) return;
    const applyJobId = pipeline.applyResult.apply_job_id;
    // React StrictMode double-invokes mount effects in dev (mount -> cleanup -> mount
    // again). This ref stops that from firing two full /recommend jobs (real 5-fold
    // CV, not cheap). Deliberately no cleanup/cancelled-flag alongside it: with
    // dispatch already deduplicated here, there's nothing left in flight to cancel on
    // the synthetic remount, and adding one anyway silently discards the one real
    // request's result the moment it resolves (this shipped broken once already).
    if (startedForRef.current === applyJobId) return;
    startedForRef.current = applyJobId;

    setLoading(true);
    setError(null);
    const targetColumn = pipeline.healthReport?.target_detection?.suggested_target;
    recommendAndWait(pipeline.datasetId, applyJobId, targetColumn, {
      onTick: (s) => setStatusText(s.status),
    })
      .then(({ result }) => pipeline.merge({ recommendations: result }))
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pipeline.applyResult]);

  if (!pipeline.applyResult) {
    return (
      <div className="card">
        <p>Apply your suggestions first to see validation and accuracy evidence.</p>
        <button className="btn btn-secondary" onClick={() => navigate("/workspace/apply")} style={{ marginTop: 12 }}>
          ← Back to Apply
        </button>
      </div>
    );
  }

  const recs = pipeline.recommendations;
  const mf = recs?.dataset_meta_features;
  const hasValidated = recs?.recommendations?.some((r) => r.benchmark?.status === "completed");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div className="page-header">
        <h1>Validation &amp; accuracy</h1>
        <p>The evidence behind the algorithm recommendation on the next step, not just a heuristic guess.</p>
      </div>

      {isPerson4Mocked && (
        <div className="mock-banner">
          Person 4's recommendation engine is running in mock mode (VITE_MOCK_PERSON4=true).
        </div>
      )}

      {loading && (
        <LoadingSpinner
          label={`Scoring candidate algorithms${statusText ? ` (${statusText})` : "..."}. Real benchmarking can take a minute or two.`}
        />
      )}
      <ErrorBanner error={error} />

      {recs && (
        <>
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <span className="badge badge-primary">{recs.task_type}</span>
            {recs.target_column && <span className="badge badge-neutral">target: {recs.target_column}</span>}
            {!recs.benchmarked && <span className="badge badge-warning">not benchmarked</span>}
          </div>

          {mf && (
            <div className="stat-grid">
              <div className="stat-tile">
                <div className="stat-value">{mf.n_rows?.toLocaleString()}</div>
                <div className="stat-label">Rows</div>
              </div>
              <div className="stat-tile">
                <div className="stat-value">{mf.n_features}</div>
                <div className="stat-label">Features</div>
              </div>
              <div className="stat-tile">
                <div className="stat-value">{mf.class_imbalance_ratio != null ? `${mf.class_imbalance_ratio}:1` : "n/a"}</div>
                <div className="stat-label">Class imbalance</div>
              </div>
              <div className="stat-tile">
                <div className="stat-value">{mf.missing_cell_pct}%</div>
                <div className="stat-label">Missing cells</div>
              </div>
            </div>
          )}

          <div className="card">
            <h3>Validation method</h3>
            <p style={{ marginTop: 4, fontSize: 13.5 }}>
              {hasValidated
                ? "The scores below aren't estimated. Each candidate marked “validated” was actually fit with real 5-fold cross-validation on your cleaned dataset: it's split into 5 parts, trained on 4, tested on the 1 held out, rotated 5 times, and the scores are averaged. That tests how the model performs on data it hasn't seen, which is the real basis for recommending one algorithm over another, not just a heuristic guess."
                : "No candidate completed empirical benchmarking for this run. See the status column below for exactly why each one was skipped or failed. The next step's ranking is meta-learning only, based on matching this dataset's measured properties against known algorithm behavior, not a measured score."}
            </p>
          </div>

          {hasValidated && (
            <>
              <div className="card">
                <h3>Score comparison</h3>
                <p style={{ marginTop: 4, fontSize: 13, color: "var(--color-text-muted)" }}>
                  Mean cross-validation score per benchmarked candidate.
                </p>
                <div style={{ marginTop: 16 }}>
                  <BenchmarkScoreChart recommendations={recs.recommendations} />
                </div>
              </div>

              <div className="card">
                <h3>Multi-metric comparison</h3>
                <p style={{ marginTop: 4, fontSize: 13, color: "var(--color-text-muted)" }}>
                  Every axis here is a real measured value, not a filler number: recommendation fit
                  and validation accuracy are absolute scores; speed and stability are ranked
                  relative to the other benchmarked candidates (there's no absolute scale for "how
                  fast" on its own).
                </p>
                <div style={{ marginTop: 16 }}>
                  <RadarComparisonChart recommendations={recs.recommendations} />
                </div>
              </div>
            </>
          )}

          <div className="card">
            <h3>Detailed results</h3>
            <div style={{ overflowX: "auto", marginTop: 12 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Algorithm</th>
                    <th>Metric</th>
                    <th>Mean score</th>
                    <th>Fold scores</th>
                    <th>Fit time</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {recs.recommendations.map((rec) => {
                    const b = rec.benchmark;
                    const validated = b?.status === "completed";
                    const statusInfo = STATUS_BADGE[b?.status ?? "none"] ?? STATUS_BADGE.none;
                    return (
                      <tr key={rec.algorithm}>
                        <td>{rec.algorithm}</td>
                        <td>{validated ? (METRIC_LABEL[b.metric] ?? b.metric) : "N/A"}</td>
                        <td className="mono">{validated ? b.score.toFixed(3) : "N/A"}</td>
                        <td className="mono" style={{ fontSize: 12 }}>
                          {validated && b.cv_scores ? b.cv_scores.map((s) => s.toFixed(2)).join(", ") : "N/A"}
                        </td>
                        <td className="mono">{validated ? `${b.fit_time_seconds?.toFixed(2)}s` : "N/A"}</td>
                        <td>
                          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
                            <span className={`badge ${statusInfo.cls}`}>{statusInfo.label}</span>
                            {b?.note && !validated && (
                              <span style={{ fontSize: 11, color: "var(--color-text-muted)" }}>{stripLongDashes(b.note)}</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button className="btn btn-primary" onClick={() => navigate("/workspace/recommend")}>
              See recommended algorithms →
            </button>
          </div>

          <div className="card" style={{ fontSize: 13 }}>
            <h3>References</h3>
            <ol style={{ margin: "8px 0 0", paddingLeft: 20, display: "flex", flexDirection: "column", gap: 10 }}>
              {REFERENCES.map((ref) => (
                <li key={ref.text}>
                  {ref.href ? (
                    <a href={ref.href} target="_blank" rel="noreferrer" style={{ color: "var(--color-primary)" }}>
                      {ref.text}
                    </a>
                  ) : (
                    <span>{ref.text}</span>
                  )}
                  <div style={{ color: "var(--color-text-muted)", fontSize: 12, marginTop: 2 }}>{ref.note}</div>
                </li>
              ))}
            </ol>
          </div>
        </>
      )}
    </div>
  );
}
