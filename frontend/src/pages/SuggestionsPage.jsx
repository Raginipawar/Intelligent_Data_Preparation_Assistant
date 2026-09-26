import { useEffect, useMemo, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePipeline } from "../context/PipelineContext";
import { suggestAndWait } from "../api/person2Api";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorBanner from "../components/ErrorBanner";
import SuggestionCard from "../components/SuggestionCard";

const TYPE_FILTERS = ["all", "imputation", "encoding", "scaling", "transform", "drop_redundant", "binning", "interaction"];

export default function SuggestionsPage() {
  const pipeline = usePipeline();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [statusText, setStatusText] = useState(null);
  const [typeFilter, setTypeFilter] = useState("all");
  const startedForRef = useRef(null);

  useEffect(() => {
    if (!pipeline.healthReport || pipeline.suggestions) return;
    // Guards against React StrictMode's dev-only double mount-effect firing this
    // twice (see the identical guard + explanation in RecommendationsPage.jsx).
    // Deliberately no cleanup/cancelled-flag here: with dispatch already
    // deduplicated by the ref above, there's nothing left in flight to cancel on
    // StrictMode's synthetic remount, and adding one anyway silently discards the
    // one real request's result the moment it resolves (this shipped broken once
    // already — the cleanup fired before the response came back and threw it away).
    if (startedForRef.current === pipeline.analysisJobId) return;
    startedForRef.current = pipeline.analysisJobId;

    setLoading(true);
    setError(null);
    suggestAndWait(pipeline.datasetId, pipeline.analysisJobId, { onTick: (s) => setStatusText(s.status) })
      .then(({ jobId, suggestionList }) => {
        pipeline.merge({
          suggestionJobId: jobId,
          suggestions: suggestionList.suggestions,
          selectedSuggestionIds: suggestionList.suggestions.map((s) => s.id),
        });
      })
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pipeline.healthReport]);

  const filtered = useMemo(() => {
    const list = pipeline.suggestions ?? [];
    return typeFilter === "all" ? list : list.filter((s) => s.type === typeFilter);
  }, [pipeline.suggestions, typeFilter]);

  if (!pipeline.healthReport) {
    return (
      <div className="card">
        <p>Run analysis first before requesting suggestions.</p>
        <button className="btn btn-secondary" onClick={() => navigate("/workspace")} style={{ marginTop: 12 }}>
          ← Back to Upload
        </button>
      </div>
    );
  }

  const selectedCount = pipeline.selectedSuggestionIds.length;
  const totalCount = pipeline.suggestions?.length ?? 0;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div className="page-header">
        <h1>Preprocessing suggestions</h1>
        <p>Ranked by expected impact. Toggle off anything you don't want applied.</p>
      </div>

      {loading && <LoadingSpinner label={`Generating suggestions${statusText ? ` (${statusText})` : "..."}`} />}
      <ErrorBanner error={error} />

      {pipeline.suggestions && (
        <>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 12 }}>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
              {TYPE_FILTERS.map((t) => (
                <button
                  key={t}
                  className="btn btn-secondary"
                  style={{ padding: "6px 12px", fontSize: 12.5, background: typeFilter === t ? "var(--color-primary-soft)" : undefined, borderColor: typeFilter === t ? "var(--color-primary)" : undefined, color: typeFilter === t ? "var(--color-primary)" : undefined }}
                  onClick={() => setTypeFilter(t)}
                >
                  {t === "all" ? "All" : t.replace("_", " ")}
                </button>
              ))}
            </div>
            <span style={{ fontSize: 13, color: "var(--color-text-muted)" }}>
              {selectedCount} / {totalCount} selected
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {filtered.map((s) => (
              <SuggestionCard
                key={s.id}
                suggestion={s}
                checked={pipeline.selectedSuggestionIds.includes(s.id)}
                onToggle={pipeline.toggleSuggestion}
              />
            ))}
            {filtered.length === 0 && <p>No suggestions of this type.</p>}
          </div>

          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <button className="btn btn-primary" disabled={selectedCount === 0} onClick={() => navigate("/workspace/apply")}>
              Apply {selectedCount} suggestion{selectedCount === 1 ? "" : "s"} →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
