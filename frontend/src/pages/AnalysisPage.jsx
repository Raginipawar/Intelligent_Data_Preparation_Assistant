import { useNavigate } from "react-router-dom";
import { usePipeline } from "../context/PipelineContext";
import MissingnessBarChart from "../components/charts/MissingnessBarChart";
import DistributionHistogram from "../components/charts/DistributionHistogram";
import CorrelationHeatmap from "../components/charts/CorrelationHeatmap";
import ImportanceBarChart from "../components/charts/ImportanceBarChart";
import { stripLongDashes } from "../utils/text";

export default function AnalysisPage() {
  const pipeline = usePipeline();
  const navigate = useNavigate();
  const report = pipeline.healthReport;

  if (!report) {
    return (
      <div className="card">
        <p>No analysis yet. Head back to Upload to run one.</p>
        <button className="btn btn-secondary" onClick={() => navigate("/workspace")} style={{ marginTop: 12 }}>
          ← Back to Upload
        </button>
      </div>
    );
  }

  const { ingestion, missingness, distributions, cardinality, correlation, target_detection, duplicates, outliers, feature_importance_signal } = report;
  const numericColumns = Object.entries(distributions?.columns ?? {});
  const isolationForest = outliers?.isolation_forest;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 24 }}>
      <div className="page-header">
        <h1>Dataset Health Report</h1>
        <p>{ingestion?.primary_file} · {ingestion?.n_rows?.toLocaleString()} rows × {ingestion?.n_columns} columns</p>
      </div>

      <div className="stat-grid">
        <div className="stat-tile">
          <div className="stat-value">{missingness?.overall_missing_pct?.toFixed(1)}%</div>
          <div className="stat-label">Overall missing</div>
        </div>
        <div className="stat-tile">
          <div className="stat-value">{duplicates?.exact_duplicate_rows ?? 0}</div>
          <div className="stat-label">Duplicate rows</div>
        </div>
        <div className="stat-tile">
          <div className="stat-value">{isolationForest ? `${(isolationForest.dataset_anomaly_rate * 100).toFixed(1)}%` : "n/a"}</div>
          <div className="stat-label">Anomaly rate</div>
        </div>
        <div className="stat-tile">
          <div className="stat-value stat-value-text">{target_detection?.suggested_target ?? "none"}</div>
          <div className="stat-label">Guessed target</div>
        </div>
      </div>

      {target_detection?.suggested_target && (
        <div className="card">
          <h3>Target detection</h3>
          <p style={{ marginTop: 6 }}>
            <strong style={{ color: "var(--color-text)" }}>{target_detection.suggested_target}</strong>
            {" "}({target_detection.task_type_guess}, confidence {Math.round(target_detection.confidence * 100)}%): {stripLongDashes(target_detection.reasoning)}
          </p>
        </div>
      )}

      <div className="card">
        <h3>Missing values by column</h3>
        <div style={{ marginTop: 12 }}>
          <MissingnessBarChart missingness={missingness} />
        </div>
      </div>

      {numericColumns.length > 0 && (
        <div className="card">
          <h3>Numeric distributions</h3>
          <div style={{ marginTop: 12, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 12 }}>
            {numericColumns.map(([col, dist]) => (
              <DistributionHistogram key={col} column={col} dist={dist} />
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <h3>Correlation matrix</h3>
        <div style={{ marginTop: 12 }}>
          <CorrelationHeatmap correlation={correlation} />
        </div>
      </div>

      {feature_importance_signal?.ran && (
        <div className="card">
          <h3>Rough feature importance</h3>
          <p style={{ marginTop: 4, marginBottom: 12, fontSize: 13 }}>{stripLongDashes(feature_importance_signal.note)}</p>
          <ImportanceBarChart importances={feature_importance_signal.importances} />
        </div>
      )}

      <div className="card">
        <h3>Cardinality</h3>
        <div style={{ overflowX: "auto", marginTop: 12 }}>
          <table className="data-table">
            <thead>
              <tr><th>Column</th><th>Unique values</th><th>Unique ratio</th><th>High cardinality</th></tr>
            </thead>
            <tbody>
              {Object.entries(cardinality?.columns ?? {}).map(([col, info]) => (
                <tr key={col}>
                  <td>{col}</td>
                  <td>{info.n_unique}</td>
                  <td>{info.unique_ratio}</td>
                  <td>{info.high_cardinality ? <span className="badge badge-warning">yes</span> : "no"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button className="btn btn-primary" onClick={() => navigate("/workspace/suggestions")}>
          Get preprocessing suggestions →
        </button>
      </div>
    </div>
  );
}
