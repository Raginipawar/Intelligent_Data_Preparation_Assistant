import { NavLink } from "react-router-dom";
import { usePipeline } from "../context/PipelineContext";

const STEPS = [
  { path: "/workspace", label: "Upload", end: true, isReady: () => true },
  { path: "/workspace/analysis", label: "Analyze", isReady: (p) => Boolean(p.datasetId) },
  { path: "/workspace/suggestions", label: "Suggest", isReady: (p) => Boolean(p.healthReport) },
  { path: "/workspace/apply", label: "Apply & Export", isReady: (p) => Boolean(p.suggestions) },
  { path: "/workspace/validation", label: "Validation", isReady: (p) => Boolean(p.applyResult) },
  { path: "/workspace/recommend", label: "Recommend", isReady: (p) => Boolean(p.recommendations) },
];

export default function StepperNav() {
  const pipeline = usePipeline();

  return (
    <nav className="stepper-nav">
      <style>{`
        .stepper-nav {
          display: flex;
          border: 1px solid var(--color-border);
          border-radius: var(--radius);
          background: var(--color-surface);
          overflow: hidden;
        }
        .stepper-nav a {
          flex: 1;
          text-align: center;
          padding: 12px 8px;
          font-size: 13px;
          font-weight: 600;
          color: var(--color-text-muted);
          text-decoration: none;
          border-right: 1px solid var(--color-border);
          position: relative;
        }
        .stepper-nav a:last-child { border-right: none; }
        .stepper-nav a.active {
          color: var(--color-primary);
          background: linear-gradient(135deg, color-mix(in srgb, var(--color-primary) 22%, transparent), color-mix(in srgb, var(--color-primary) 8%, transparent));
          backdrop-filter: blur(6px);
          -webkit-backdrop-filter: blur(6px);
          box-shadow: inset 0 1px 0 color-mix(in srgb, var(--color-primary) 25%, white 10%);
        }
        .stepper-nav a.disabled { pointer-events: none; opacity: 0.4; }
        .stepper-nav .step-index {
          display: inline-block;
          width: 18px; height: 18px;
          line-height: 18px;
          border-radius: 50%;
          background: var(--color-border);
          color: var(--color-text);
          font-size: 11px;
          margin-right: 6px;
        }
        .stepper-nav a.active .step-index { background: var(--color-primary); color: white; }
      `}</style>
      {STEPS.map((step, i) => {
        const ready = step.isReady(pipeline);
        return (
          <NavLink
            key={step.path}
            to={step.path}
            end={step.end}
            className={({ isActive }) => [isActive ? "active" : "", ready ? "" : "disabled"].join(" ")}
          >
            <span className="step-index">{i + 1}</span>
            {step.label}
          </NavLink>
        );
      })}
    </nav>
  );
}
