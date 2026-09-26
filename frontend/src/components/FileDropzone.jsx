import { useRef, useState } from "react";

const ACCEPTED_EXTENSIONS = [".csv", ".zip"];

function isAccepted(file) {
  const name = file.name.toLowerCase();
  return ACCEPTED_EXTENSIONS.some((ext) => name.endsWith(ext));
}

export default function FileDropzone({ onFileSelected, disabled }) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef(null);

  const handleFiles = (files) => {
    const file = files?.[0];
    if (!file) return;
    if (!isAccepted(file)) {
      onFileSelected(null, `'${file.name}' isn't a .csv or .zip file.`);
      return;
    }
    onFileSelected(file, null);
  };

  return (
    <div
      className="dropzone"
      data-dragging={isDragging}
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        if (!disabled) handleFiles(e.dataTransfer.files);
      }}
      onClick={() => !disabled && inputRef.current?.click()}
    >
      <style>{`
        .dropzone {
          border: 2px dashed var(--color-border);
          border-radius: var(--radius);
          padding: 40px 20px;
          text-align: center;
          cursor: pointer;
          background: var(--color-surface);
          transition: border-color 0.15s ease, background 0.15s ease;
        }
        .dropzone:hover { border-color: var(--color-primary); }
        .dropzone[data-dragging="true"] { border-color: var(--color-primary); background: var(--color-primary-soft); }
      `}</style>
      <input
        ref={inputRef}
        type="file"
        accept=".csv,.zip"
        hidden
        disabled={disabled}
        onChange={(e) => handleFiles(e.target.files)}
      />
      <p style={{ fontWeight: 600, color: "var(--color-text)", marginBottom: 4 }}>
        Drop a CSV or ZIP file here, or click to browse
      </p>
      <p>Single CSV, or a ZIP of related CSVs</p>
    </div>
  );
}
