import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { usePipeline } from "../context/PipelineContext";
import { applyAndWait, exportDataset, isPerson3Mocked } from "../api/person3Api";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorBanner from "../components/ErrorBanner";
import { stripLongDashes } from "../utils/text";

function downloadBlob(blob, fileName) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

const SKIPPED_LABEL = {
  skipped_conflict: "conflict",
  skipped_not_selected: "not selected",
  skipped_missing_column: "missing column",
  skipped_error: "error",
};

export default function ApplyExportPage() {
  const pipeline = usePipeline();
  const navigate = useNavigate();
  const [applying, setApplying] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);

  if (!pipeline.suggestions) {
    return (
      <div className="card">
        <p>Get suggestions first before applying anything.</p>
        <button className="btn btn-secondary" onClick={() => navigate("/workspace/suggestions")} style={{ marginTop: 12 }}>
          ← Back to Suggestions
        </button>
      </div>
    );
  }

  const handleApply = async () => {
    setError(null);
    setApplying(true);
    try {
      const targetColumn = pipeline.healthReport?.target_detection?.suggested_target;
      const { result } = await applyAndWait(
        pipeline.datasetId,
        pipeline.suggestionJobId,
        pipeline.selectedSuggestionIds,
        {
          targetColumn,
          allSuggestions: pipeline.suggestions,
          originalColumnCount: pipeline.ingestion?.n_columns,
        }
      );
      pipeline.merge({ applyResult: result });
    } catch (err) {
      setError(err);
    } finally {
      setApplying(false);
    }
  };

  const handleExport = async () => {
    setError(null);
    setExporting(true);
    try {
      const blob = await exportDataset(pipeline.applyResult.apply_job_id, "auto");
      downloadBlob(blob, `cleaned_${pipeline.fileName ?? "dataset.csv"}`);
    } catch (err) {
      setError(err);
    } finally {
      setExporting(false);
    }
  };

  const result = pipeline.applyResult;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div className="page-header">
        <h1>Apply & export</h1>
        <p>Applies your selected suggestions in a safe order and produces the cleaned dataset.</p>
      </div>

      {isPerson3Mocked && (
        <div className="mock-banner">
          Person 3's apply/export engine is running in mock mode (VITE_MOCK_PERSON3=true).
        </div>
      )}

      <ErrorBanner error={error} />

      {!result && (
        <button className="btn btn-primary" onClick={handleApply} disabled={applying} style={{ alignSelf: "flex-start" }}>
          {applying ? <LoadingSpinner label="Applying..." /> : `Apply ${pipeline.selectedSuggestionIds.length} suggestions`}
        </button>
      )}

      {result && (
        <>
          <div className="stat-grid">
            <div className="stat-tile">
              <div className="stat-value">{result.applied_suggestions.length}</div>
              <div className="stat-label">Applied</div>
            </div>
            <div className="stat-tile">
              <div className="stat-value">{result.skipped_suggestions.length}</div>
              <div className="stat-label">Skipped</div>
            </div>
            <div className="stat-tile">
              <div className="stat-value">{result.n_rows ?? "N/A"}</div>
              <div className="stat-label">Rows</div>
            </div>
            <div className="stat-tile">
              <div className="stat-value">{result.n_columns ?? "N/A"}</div>
              <div className="stat-label">Final columns</div>
            </div>
          </div>

          {result.skipped_suggestions.length > 0 && (
            <div className="card">
              <h3>Skipped</h3>
              <div style={{ overflowX: "auto", marginTop: 12 }}>
                <table className="data-table">
                  <thead>
                    <tr><th>Suggestion</th><th>Why</th><th>Status</th></tr>
                  </thead>
                  <tbody>
                    {result.skipped_suggestions.map((s) => (
                      <tr key={s.suggestion_id}>
                        <td className="mono">{s.suggestion_id}</td>
                        <td>{stripLongDashes(s.reasoning)}</td>
                        <td><span className="badge badge-warning">{SKIPPED_LABEL[s.status] ?? s.status}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <div className="card">
            <h3>Transformation log</h3>
            <div style={{ overflowX: "auto", marginTop: 12 }}>
              <table className="data-table">
                <thead>
                  <tr><th>#</th><th>Type</th><th>Column(s)</th><th>Action</th></tr>
                </thead>
                <tbody>
                  {result.transformation_log.map((entry) => (
                    <tr key={entry.order}>
                      <td>{entry.order}</td>
                      <td><span className="badge badge-primary">{entry.type}</span></td>
                      <td className="mono">{entry.target_columns.join(", ")}</td>
                      <td>{stripLongDashes(entry.action)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <button className="btn btn-secondary" onClick={handleExport} disabled={exporting}>
              {exporting ? <LoadingSpinner label="Exporting..." /> : "⬇ Download cleaned dataset"}
            </button>
            <button className="btn btn-primary" onClick={() => navigate("/workspace/validation")}>
              See validation & accuracy →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
