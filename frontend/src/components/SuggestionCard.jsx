import { stripLongDashes } from "../utils/text";

const TYPE_LABEL = {
  imputation: "Imputation",
  encoding: "Encoding",
  scaling: "Scaling",
  transform: "Transform",
  drop_redundant: "Drop redundant",
  binning: "Binning",
  interaction: "Interaction",
};

function paramsSummary(suggestion) {
  const { type, params = {} } = suggestion;
  switch (type) {
    case "imputation":
      return `strategy: ${params.strategy}`;
    case "encoding":
      return `method: ${params.method}`;
    case "scaling":
      return `method: ${params.method}`;
    case "transform":
      return `function: ${params.function}`;
    case "drop_redundant":
      return params.kept_column ? `keeping: ${params.kept_column}` : params.reason;
    case "binning":
      return `${params.strategy}, ${params.n_bins} bins`;
    case "interaction":
      return `new column: ${params.new_column}`;
    default:
      return null;
  }
}

export default function SuggestionCard({ suggestion, checked, onToggle }) {
  const summary = paramsSummary(suggestion);

  return (
    <label className="card suggestion-card" data-checked={checked}>
      <style>{`
        .suggestion-card {
          display: flex;
          gap: 14px;
          align-items: flex-start;
          cursor: pointer;
        }
        .suggestion-card[data-checked="true"] {
          border-color: var(--color-primary);
          box-shadow: 0 0 0 1px var(--color-primary);
        }
        .suggestion-card input { margin-top: 3px; width: 16px; height: 16px; flex-shrink: 0; }
        .suggestion-card .columns { font-family: var(--font-mono); font-size: 12.5px; color: var(--color-text); }
      `}</style>
      <input type="checkbox" checked={checked} onChange={() => onToggle(suggestion.id)} />
      <div style={{ display: "flex", flexDirection: "column", gap: 6, flex: 1 }}>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <span className="badge badge-primary">{TYPE_LABEL[suggestion.type] ?? suggestion.type}</span>
          <span className="badge badge-neutral">rank #{suggestion.priority_rank}</span>
          <span className="badge badge-neutral">confidence {Math.round(suggestion.confidence * 100)}%</span>
          {suggestion.source?.includes("autogluon") && <span className="badge badge-success">AutoGluon-corroborated</span>}
        </div>
        <div className="columns">{suggestion.target_columns.join(", ")}</div>
        <p style={{ fontSize: 13.5 }}>{stripLongDashes(suggestion.reasoning)}</p>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12.5 }}>
          <span style={{ color: "var(--color-text-muted)" }}>{stripLongDashes(suggestion.expected_impact)}</span>
          {summary && <span className="mono" style={{ color: "var(--color-text-muted)" }}>{summary}</span>}
        </div>
      </div>
    </label>
  );
}
