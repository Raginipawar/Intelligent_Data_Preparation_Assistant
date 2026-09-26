import { useState } from "react";
import { useNavigate } from "react-router-dom";
import FileDropzone from "../components/FileDropzone";
import LoadingSpinner from "../components/LoadingSpinner";
import ErrorBanner from "../components/ErrorBanner";
import { usePipeline } from "../context/PipelineContext";
import { uploadDataset, analyzeAndWait } from "../api/person1Api";
import { stripLongDashes } from "../utils/text";

export default function UploadPage() {
  const pipeline = usePipeline();
  const navigate = useNavigate();
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeStatus, setAnalyzeStatus] = useState(null);
  const [error, setError] = useState(null);

  const handleFile = async (file, validationError) => {
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    setUploading(true);
    pipeline.reset();
    try {
      const result = await uploadDataset(file);
      pipeline.merge({
        datasetId: result.dataset_id,
        fileName: file.name,
        ingestion: result.ingestion,
        schema: result.schema,
      });
    } catch (err) {
      setError(err);
    } finally {
      setUploading(false);
    }
  };

  const handleAnalyze = async () => {
    setError(null);
    setAnalyzing(true);
    try {
      const { jobId, report } = await analyzeAndWait(pipeline.datasetId, {
        onTick: (status) => setAnalyzeStatus(status.status),
      });
      pipeline.merge({ analysisJobId: jobId, healthReport: report });
      navigate("/workspace/analysis");
    } catch (err) {
      setError(err);
    } finally {
      setAnalyzing(false);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      <div className="page-header">
        <h1>Upload your dataset</h1>
        <p>CSV or ZIP. We'll ingest it and run a full statistical health check next.</p>
      </div>

      <FileDropzone onFileSelected={handleFile} disabled={uploading || analyzing} />
      {uploading && <LoadingSpinner label="Uploading and parsing..." />}
      <ErrorBanner error={error} />

      {pipeline.ingestion && (
        <div className="card" style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h3>{pipeline.fileName}</h3>
            <span className="badge badge-success">Uploaded</span>
          </div>
          <div className="stat-grid">
            <div className="stat-tile">
              <div className="stat-value">{pipeline.ingestion.n_rows.toLocaleString()}</div>
              <div className="stat-label">Rows</div>
            </div>
            <div className="stat-tile">
              <div className="stat-value">{pipeline.ingestion.n_columns}</div>
              <div className="stat-label">Columns</div>
            </div>
            <div className="stat-tile">
              <div className="stat-value">{pipeline.ingestion.malformed_rows_skipped}</div>
              <div className="stat-label">Malformed rows skipped</div>
            </div>
            <div className="stat-tile">
              <div className="stat-value">{pipeline.ingestion.encoding}</div>
              <div className="stat-label">Encoding</div>
            </div>
          </div>
          {pipeline.ingestion.parsing_warnings?.length > 0 && (
            <div className="mock-banner">{pipeline.ingestion.parsing_warnings.map(stripLongDashes).join(" · ")}</div>
          )}

          <button className="btn btn-primary" onClick={handleAnalyze} disabled={analyzing} style={{ alignSelf: "flex-start" }}>
            {analyzing ? <LoadingSpinner label={`Analyzing${analyzeStatus ? ` (${analyzeStatus})` : "..."}`} /> : "Run deep analysis →"}
          </button>
        </div>
      )}
    </div>
  );
}
