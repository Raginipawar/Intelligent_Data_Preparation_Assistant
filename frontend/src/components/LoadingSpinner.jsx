export default function LoadingSpinner({ label }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <div className="spinner" />
      {label && <span style={{ color: "var(--color-text-muted)", fontSize: 14 }}>{label}</span>}
    </div>
  );
}
