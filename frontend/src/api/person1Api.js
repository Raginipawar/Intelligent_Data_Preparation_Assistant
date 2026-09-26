// person1Api.js — client for Person 1's Ingestion & Deep Analysis engine.
// See person1_engine/README.md for the live contract.

import { apiFetch, apiPostForm, pollJob } from "./client";

const BASE_URL = import.meta.env.VITE_PERSON1_API_URL;

export async function uploadDataset(file) {
  const formData = new FormData();
  formData.append("file", file);
  // Fast + synchronous — returns { dataset_id, ingestion, schema } immediately.
  return apiPostForm(`${BASE_URL}/upload`, formData);
}

export async function startAnalysis(datasetId) {
  // Kicks off the heavy stats/ML pass as a background job.
  return apiFetch(`${BASE_URL}/analyze?dataset_id=${encodeURIComponent(datasetId)}`, { method: "POST" });
}

// Resolves with the full Dataset Health Report once the analyze job finishes.
export async function analyzeAndWait(datasetId, { onTick } = {}) {
  const { job_id: jobId } = await startAnalysis(datasetId);
  const report = await pollJob(BASE_URL, jobId, { onTick, timeoutMs: 120000 });
  return { jobId, report };
}

export const person1BaseUrl = BASE_URL;
