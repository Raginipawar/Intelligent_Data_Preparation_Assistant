// person2Api.js — client for Person 2's Preprocessing & Feature Engineering
// Suggestion engine. See person2_engine/README.md for the live contract.

import { apiPostJson, pollJob } from "./client";

const BASE_URL = import.meta.env.VITE_PERSON2_API_URL;

export async function startSuggestions(datasetId, sourceJobId) {
  // dataset_id + source_job_id: this engine fetches Person 1's health report
  // itself from shared local storage (see person2_engine/app/health_report_client.py) —
  // the frontend never needs to pass the report body inline for the integrated flow.
  return apiPostJson(`${BASE_URL}/suggest`, { dataset_id: datasetId, source_job_id: sourceJobId });
}

// Resolves with the full ranked Suggestion List once the job finishes.
export async function suggestAndWait(datasetId, sourceJobId, { onTick } = {}) {
  const { job_id: jobId } = await startSuggestions(datasetId, sourceJobId);
  const suggestionList = await pollJob(BASE_URL, jobId, { onTick, timeoutMs: 60000 });
  return { jobId, suggestionList };
}

export const person2BaseUrl = BASE_URL;
