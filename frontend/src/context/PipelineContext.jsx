// PipelineContext.jsx — single source of truth for the wizard's state as it
// flows Upload -> Analyze -> Suggest -> Apply -> Recommend. Kept as one flat
// object + a merge-style updater rather than per-page local state, since later
// steps need earlier steps' data (e.g. Suggestions needs Person 1's job_id,
// Apply needs Person 2's suggestions, Recommend needs the target's task type).
import { createContext, useContext, useMemo, useState } from "react";

const PipelineContext = createContext(null);

const initialState = {
  // Upload
  datasetId: null,
  fileName: null,
  ingestion: null,
  schema: null,

  // Analyze (Person 1)
  analysisJobId: null,
  healthReport: null,

  // Suggest (Person 2)
  suggestionJobId: null,
  suggestions: null,
  selectedSuggestionIds: [],

  // Apply & Export (Person 3, mocked for now)
  applyResult: null,

  // Recommend (Person 4, mocked for now)
  recommendations: null,
};

export function PipelineProvider({ children }) {
  const [state, setState] = useState(initialState);

  const merge = (partial) => setState((prev) => ({ ...prev, ...partial }));
  const reset = () => setState(initialState);

  const toggleSuggestion = (id) =>
    setState((prev) => ({
      ...prev,
      selectedSuggestionIds: prev.selectedSuggestionIds.includes(id)
        ? prev.selectedSuggestionIds.filter((existing) => existing !== id)
        : [...prev.selectedSuggestionIds, id],
    }));

  const setSelectedSuggestionIds = (ids) => merge({ selectedSuggestionIds: ids });

  const value = useMemo(
    () => ({ ...state, merge, reset, toggleSuggestion, setSelectedSuggestionIds }),
    [state]
  );

  return <PipelineContext.Provider value={value}>{children}</PipelineContext.Provider>;
}

export function usePipeline() {
  const ctx = useContext(PipelineContext);
  if (!ctx) throw new Error("usePipeline must be used within a PipelineProvider");
  return ctx;
}
