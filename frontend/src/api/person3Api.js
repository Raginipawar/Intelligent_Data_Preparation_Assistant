// person3Api.js — client for Person 3's Execution/Transform (apply) engine.
// See person3_engine/README.md for the live contract. Confirmed against the
// real running engine (not just docs) — response shapes here are what it
// actually returns: applied_suggestions/skipped_suggestions/transformation_log
// with a `status` field per entry, flat final_columns/n_rows/n_columns (no
// nested final_shape), and export as its own POST keyed by apply_job_id.
//
// Falls back to src/mocks/person3Mock.js if VITE_MOCK_PERSON3=true (useful for
// frontend-only dev without the Python engines running) — see .env.development.

import { apiPostJson, apiPostJsonForBlob, pollJob } from "./client";
import { mockApply, mockExport } from "../mocks/person3Mock";

const BASE_URL = import.meta.env.VITE_PERSON3_API_URL;
const USE_MOCK = import.meta.env.VITE_MOCK_PERSON3 === "true";

export async function startApply(datasetId, sourceJobId, selectedSuggestionIds, { targetColumn, featureBudget } = {}) {
  const body = {
    dataset_id: datasetId,
    source_job_id: sourceJobId,
    selected_suggestion_ids: selectedSuggestionIds,
  };
  if (targetColumn) body.target_column = targetColumn;
  if (featureBudget) body.feature_budget = featureBudget;
  return apiPostJson(`${BASE_URL}/apply`, body);
}

// Resolves with the full ApplyResult once the job finishes.
export async function applyAndWait(datasetId, sourceJobId, selectedSuggestionIds, opts = {}) {
  if (USE_MOCK) {
    const result = await mockApply(datasetId, selectedSuggestionIds, opts.allSuggestions, opts.originalColumnCount);
    return { jobId: result.apply_job_id, result };
  }
  const { job_id: jobId } = await startApply(datasetId, sourceJobId, selectedSuggestionIds, opts);
  const result = await pollJob(BASE_URL, jobId, { timeoutMs: 60000, onTick: opts.onTick });
  return { jobId, result };
}

export async function exportDataset(applyJobId, format = "auto") {
  if (USE_MOCK) {
    return mockExport(applyJobId);
  }
  return apiPostJsonForBlob(`${BASE_URL}/export`, { apply_job_id: applyJobId, format });
}

export const isPerson3Mocked = USE_MOCK;
export const person3BaseUrl = BASE_URL;
