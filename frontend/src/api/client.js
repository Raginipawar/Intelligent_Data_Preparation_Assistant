// client.js — thin fetch wrapper shared by every engine's API module.
// Every engine (Person 1/2, and eventually 3/4) speaks the same shape:
// JSON in, JSON out, errors as {"error": "..."} or FastAPI's {"detail": "..."}.

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function parseErrorBody(response) {
  try {
    const body = await response.json();
    return body.detail || body.error || JSON.stringify(body);
  } catch {
    return response.statusText;
  }
}

export async function apiFetch(url, options = {}) {
  const response = await fetch(url, options);
  if (!response.ok && response.status !== 202) {
    const message = await parseErrorBody(response);
    throw new ApiError(message, response.status);
  }
  return response.json();
}

export async function apiPostJson(url, body) {
  return apiFetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export async function apiPostForm(url, formData) {
  return apiFetch(url, { method: "POST", body: formData });
}

// Same error handling as apiFetch, but resolves with a Blob instead of parsed
// JSON — for file-download endpoints (e.g. Person 3's /export).
export async function apiPostJsonForBlob(url, body) {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const message = await parseErrorBody(response);
    throw new ApiError(message, response.status);
  }
  return response.blob();
}

// Polls GET {baseUrl}/status/{jobId} until status is "success" or "failed",
// then resolves with GET {baseUrl}/result/{jobId}. Every engine (Person 1's
// /analyze, Person 2's /suggest, and — once built — Person 3/4's job-backed
// endpoints) shares this exact polling shape, so one poller covers all of them.
export async function pollJob(baseUrl, jobId, { intervalMs = 700, timeoutMs = 60000, onTick } = {}) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const statusBody = await apiFetch(`${baseUrl}/status/${jobId}`);
    onTick?.(statusBody);
    if (statusBody.status === "success") {
      return apiFetch(`${baseUrl}/result/${jobId}`);
    }
    if (statusBody.status === "failed") {
      throw new ApiError(statusBody.error || "Job failed", 500);
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs));
  }
  throw new ApiError(`Timed out waiting for job ${jobId}`, 504);
}
