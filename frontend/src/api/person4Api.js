// person4Api.js — client for Person 4's Algorithm Recommendation engine.
// See person4_engine/README.md for the live contract. Confirmed against the
// real running engine — recommendations[].reasoning is an ARRAY of strings
// (not one string), benchmark is a nested object (null for candidates past
// top_k_benchmark), and dataset_meta_features is a rich object worth showing.
//
// Falls back to src/mocks/person4Mock.js if VITE_MOCK_PERSON4=true.

import { apiPostJson, pollJob } from "./client";
import { mockRecommend } from "../mocks/person4Mock";

const BASE_URL = import.meta.env.VITE_PERSON4_API_URL;
const USE_MOCK = import.meta.env.VITE_MOCK_PERSON4 === "true";

export async function startRecommend(datasetId, applyJobId, targetColumn, { performBenchmark = true, topKBenchmark = 3 } = {}) {
  return apiPostJson(`${BASE_URL}/recommend`, {
    dataset_id: datasetId,
    apply_job_id: applyJobId,
    target_column: targetColumn,
    perform_benchmark: performBenchmark,
    top_k_benchmark: topKBenchmark,
  });
}

// Resolves with the full Algorithm Recommendation Report once the job finishes.
// Real cross-validation benchmarking on messy/wide data can legitimately take
// a minute or more (observed ~52s in local testing against a 1220-row, still
// text/high-cardinality-heavy dataset) — generous timeout, slower poll interval.
export async function recommendAndWait(datasetId, applyJobId, targetColumn, opts = {}) {
  if (USE_MOCK) {
    const result = await mockRecommend(datasetId, opts.taskTypeGuess);
    return { jobId: result.job_id, result };
  }
  const { job_id: jobId } = await startRecommend(datasetId, applyJobId, targetColumn, opts);
  const result = await pollJob(BASE_URL, jobId, { timeoutMs: 180000, intervalMs: 1500, onTick: opts.onTick });
  return { jobId, result };
}

export const isPerson4Mocked = USE_MOCK;
export const person4BaseUrl = BASE_URL;
