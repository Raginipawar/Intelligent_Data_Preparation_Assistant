// person3Mock.js — stands in for Person 3's /apply + /export when
// VITE_MOCK_PERSON3=true (frontend-only dev without the Python engines
// running). Shape matches the REAL engine's response exactly — confirmed via
// live curl testing against person3_engine, not just its README — so swapping
// back and forth between mock and real is transparent to every caller.

import { STAGE_ORDER } from "../utils/stageOrder";

function actionDescription(suggestion) {
  const { type, params = {} } = suggestion;
  switch (type) {
    case "imputation":
      return `filled missing values in using strategy '${params.strategy}'`;
    case "encoding":
      return `encoded using method '${params.method}'`;
    case "scaling":
      return `scaled using method '${params.method}'`;
    case "transform":
      return `applied ${params.function} transform`;
    case "drop_redundant":
      return `dropped column (${params.reason || "redundant"})`;
    case "binning":
      return `binned into ${params.n_bins ?? "N"} buckets (${params.strategy})`;
    case "interaction":
      return `created interaction column '${params.new_column ?? "?"}'`;
    default:
      return "applied";
  }
}

export async function mockApply(datasetId, selectedIds, allSuggestions, originalColumnCount) {
  await new Promise((resolve) => setTimeout(resolve, 500));

  const applyJobId = `mock-apply-${Date.now()}`;
  const all = allSuggestions ?? [];
  const selected = all.filter((s) => selectedIds.includes(s.id));
  const ordered = [...selected].sort((a, b) => STAGE_ORDER.indexOf(a.type) - STAGE_ORDER.indexOf(b.type));

  const transformationLog = [];
  const droppedColumns = new Set();
  const newColumns = new Set();

  ordered.forEach((suggestion, i) => {
    transformationLog.push({
      order: i + 1,
      suggestion_id: suggestion.id,
      type: suggestion.type,
      target_columns: suggestion.target_columns,
      action: actionDescription(suggestion),
      reasoning: suggestion.reasoning,
      status: "applied",
    });
    if (suggestion.type === "drop_redundant") {
      suggestion.target_columns.forEach((c) => droppedColumns.add(c));
    }
    if (suggestion.type === "interaction" && suggestion.params?.new_column) {
      newColumns.add(suggestion.params.new_column);
    }
  });

  const skippedSuggestions = all
    .filter((s) => !selectedIds.includes(s.id))
    .map((s) => ({
      suggestion_id: s.id,
      type: s.type,
      target_columns: s.target_columns,
      reasoning: "Not in selected_suggestion_ids.",
      status: "skipped_not_selected",
    }));

  const finalColumnCount = Math.max(0, (originalColumnCount ?? 0) - droppedColumns.size + newColumns.size);

  return {
    dataset_id: datasetId,
    apply_job_id: applyJobId,
    source_job_id: null,
    status: "success",
    applied_suggestions: ordered.map((s) => s.id),
    skipped_suggestions: skippedSuggestions,
    transformation_log: transformationLog,
    final_columns: [],
    n_rows: null,
    n_columns: finalColumnCount || null,
    meta: { generated_at: new Date().toISOString(), engine_version: "mock", processing_time_seconds: 0.5 },
    _mock: true,
  };
}

export async function mockExport(applyJobId) {
  await new Promise((resolve) => setTimeout(resolve, 300));
  const csvContent = `# mock export — Person 3's real /export wasn't used this session\napply_job_id,${applyJobId}\n`;
  return new Blob([csvContent], { type: "text/csv" });
}
