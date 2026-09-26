import { useState } from "react";
import { DIVERGING, divergingCellColor, divergingCellTextColor } from "./chartColors";

export default function CorrelationHeatmap({ correlation }) {
  const [hovered, setHovered] = useState(null);
  const columns = Object.keys(correlation?.matrix ?? {});

  if (columns.length < 2) {
    return <p>Fewer than two numeric columns, so there's no correlation matrix to show.</p>;
  }

  const cellSize = Math.max(32, Math.min(56, Math.floor(480 / columns.length)));

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div style={{ overflowX: "auto" }}>
        <div style={{ display: "inline-grid", gridTemplateColumns: `120px repeat(${columns.length}, ${cellSize}px)` }}>
          <div />
          {columns.map((col) => (
            <div key={col} className="heatmap-col-label" style={{ writingMode: "vertical-rl", transform: "rotate(180deg)" }}>
              {col}
            </div>
          ))}
          {columns.map((rowCol) => (
            <div key={rowCol} style={{ display: "contents" }}>
              <div className="heatmap-row-label">{rowCol}</div>
              {columns.map((colCol) => {
                const value = correlation.matrix[rowCol]?.[colCol];
                const isSelf = rowCol === colCol;
                return (
                  <div
                    key={colCol}
                    className="heatmap-cell"
                    style={{
                      width: cellSize,
                      height: cellSize,
                      background: isSelf ? "var(--color-border)" : divergingCellColor(value),
                      color: isSelf ? "var(--color-text-muted)" : divergingCellTextColor(value),
                    }}
                    onMouseEnter={() => setHovered({ rowCol, colCol, value })}
                    onMouseLeave={() => setHovered(null)}
                  >
                    {value != null ? value.toFixed(2) : "–"}
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      <style>{`
        .heatmap-col-label, .heatmap-row-label {
          font-size: 11px;
          color: var(--color-text-muted);
          display: flex;
          align-items: center;
          justify-content: center;
          padding: 2px;
          overflow: hidden;
          text-overflow: ellipsis;
        }
        .heatmap-row-label { justify-content: flex-end; padding-right: 8px; white-space: nowrap; }
        .heatmap-cell {
          display: flex; align-items: center; justify-content: center;
          font-size: 11px; font-variant-numeric: tabular-nums;
          border: 2px solid var(--color-surface);
          border-radius: 3px;
          cursor: default;
        }
      `}</style>

      <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 12, color: "var(--color-text-muted)" }}>
        <span>-1</span>
        <div style={{ width: 120, height: 10, borderRadius: 4, background: `linear-gradient(to right, ${DIVERGING.negativePole}, ${DIVERGING.midpoint}, ${DIVERGING.positivePole})` }} />
        <span>+1</span>
        {hovered && (
          <span className="mono" style={{ marginLeft: "auto" }}>
            {hovered.rowCol} × {hovered.colCol}: {hovered.value?.toFixed(4) ?? "n/a"}
          </span>
        )}
      </div>
    </div>
  );
}
