// person4Mock.js — stands in for Person 4's /recommend when VITE_MOCK_PERSON4=true.
// Shape matches the REAL engine's response exactly — confirmed via live curl
// testing against person4_engine: reasoning is an array of strings per
// candidate (not one string), benchmark is a nested object, and
// dataset_meta_features is a full object alongside the ranked list.

const CLASSIFICATION_CANDIDATES = [
  { algorithm: "GradientBoostingClassifier", model_class: "sklearn.ensemble.GradientBoostingClassifier", recommendation_score: 0.93, suitability: "high", reasoning: ["Dataset size provides a balanced volume suitable for standard cross-validated estimators.", "Mixed categorical/boolean features; tree-based models split natively across mixed feature types."], benchmark: { metric: "accuracy", score: 0.79, cv_scores: [0.8, 0.79, 0.78, 0.79, 0.8], fit_time_seconds: 1.2, status: "completed", note: null } },
  { algorithm: "RandomForestClassifier", model_class: "sklearn.ensemble.RandomForestClassifier", recommendation_score: 0.9, suitability: "high", reasoning: ["Robust baseline, resistant to outliers left over after preprocessing."], benchmark: { metric: "accuracy", score: 0.77, cv_scores: [0.78, 0.76, 0.77, 0.78, 0.76], fit_time_seconds: 0.9, status: "completed", note: null } },
  { algorithm: "LogisticRegression", model_class: "sklearn.linear_model.LogisticRegression", recommendation_score: 0.75, suitability: "medium", reasoning: ["Fast, interpretable linear baseline once categoricals are properly encoded."], benchmark: null },
];

const REGRESSION_CANDIDATES = [
  { algorithm: "HistGradientBoostingRegressor", model_class: "sklearn.ensemble.HistGradientBoostingRegressor", recommendation_score: 0.94, suitability: "high", reasoning: ["Gradient-boosted trees handle non-linear relationships and mixed feature types without heavy preprocessing."], benchmark: { metric: "r2", score: 0.86, cv_scores: [0.87, 0.85, 0.86, 0.86, 0.85], fit_time_seconds: 1.4, status: "completed", note: null } },
  { algorithm: "RandomForestRegressor", model_class: "sklearn.ensemble.RandomForestRegressor", recommendation_score: 0.88, suitability: "high", reasoning: ["Robust baseline, resistant to outliers not fully addressed in preprocessing."], benchmark: { metric: "r2", score: 0.81, cv_scores: [0.82, 0.8, 0.81, 0.82, 0.8], fit_time_seconds: 1.0, status: "completed", note: null } },
  { algorithm: "Ridge", model_class: "sklearn.linear_model.Ridge", recommendation_score: 0.72, suitability: "medium", reasoning: ["Interpretable linear baseline; useful for sanity-checking the tree-based candidates above."], benchmark: null },
];

export async function mockRecommend(datasetId, taskTypeGuess) {
  await new Promise((resolve) => setTimeout(resolve, 500));
  const taskType = taskTypeGuess === "regression" ? "regression" : "binary_classification";
  const candidates = taskTypeGuess === "regression" ? REGRESSION_CANDIDATES : CLASSIFICATION_CANDIDATES;
  const recommendations = candidates.map((c, i) => ({ ...c, rank: i + 1 }));

  return {
    status: "success",
    job_id: `mock-recommend-${Date.now()}`,
    dataset_id: datasetId,
    apply_job_id: null,
    task_type: taskType,
    target_column: null,
    dataset_meta_features: null,
    recommendations,
    benchmarked: true,
    meta: { engine_version: "mock", processing_time_seconds: 0.5 },
    _mock: true,
  };
}
