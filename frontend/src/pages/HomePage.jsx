// Copyright (c) Ragini Pawar. All rights reserved.
// Original design, layout, and copy for the AutoML marketing site — not to be
// copied, cloned, or reproduced without permission.
import { useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import NavBar from "../components/NavBar";
import Particles from "../components/effects/Particles";
import GradualBlur from "../components/effects/GradualBlur";
import BorderGlow from "../components/effects/BorderGlow";
import SplashCursor from "../components/effects/SplashCursor";

const STEPS = [
  { n: "01", title: "Analyze", body: "We profile your dataset for missing values, outliers, skewed columns, and correlations, then explain what each one actually means for your data." },
  { n: "02", title: "Suggest", body: "Real AutoML-driven suggestions for cleaning and engineering your data, each one with a plain-language reason attached, not a black box." },
  { n: "03", title: "Apply & export", body: "Toggle the fixes you want. Get back a clean, model-ready dataset, plus a full log of exactly what changed and why." },
  { n: "04", title: "Recommend", body: "A ranked shortlist of ML algorithms suited to your cleaned data, so you know what to try next, not just that your data is 'ready'." },
];

const AUDIENCES = [
  { title: "Students", body: "Learn what \"clean your data\" actually means, with reasoning attached to every suggestion instead of a checklist to follow blindly." },
  { title: "Researchers", body: "Skip the repetitive manual prep on a new dataset and get straight to the modeling question you actually care about." },
  { title: "ML beginners", body: "No data science background required. Every step explains itself in plain language before you touch a single hyperparameter." },
];

const DELIVERABLES = [
  { title: "Dataset Health Report", body: "Missingness, distributions, cardinality, correlations, outliers, and a guessed target column, all in one place." },
  { title: "Suggestion List", body: "Ranked preprocessing & feature-engineering suggestions, each with reasoning and expected impact." },
  { title: "Cleaned dataset", body: "Your selected fixes applied in a safe order, exported back in your original format." },
  { title: "Algorithm shortlist", body: "Candidate ML algorithms ranked for your specific data, with the reasoning behind each pick." },
];

const GLOW_COLORS = ["#818cf8", "#38bdf8", "#f472b6"];

function GlowCard({ children }) {
  return (
    <BorderGlow
      backgroundColor="var(--color-surface)"
      borderRadius={14}
      glowRadius={26}
      glowIntensity={0.85}
      coneSpread={30}
      colors={GLOW_COLORS}
      className="feature-card-glow"
    >
      {children}
    </BorderGlow>
  );
}

export default function HomePage() {
  const location = useLocation();

  useEffect(() => {
    if (!location.hash) return;
    const el = document.querySelector(location.hash);
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [location.hash]);

  return (
    <div>
      {/* Lavender fluid cursor trail — homepage only, unmounts on navigation
          since it's tied to this component's lifecycle (see SplashCursor.jsx). */}
      <SplashCursor RAINBOW_MODE={false} COLOR="#c4b5fd" SPLAT_RADIUS={0.15} DENSITY_DISSIPATION={3.2} />

      <NavBar />

      <section className="hero">
        <div className="hero-particles">
          <Particles
            particleColors={["#c4b5fd", "#a5b4fc", "#f5d0fe"]}
            particleCount={140}
            particleSpread={12}
            speed={0.06}
            particleBaseSize={70}
            alphaParticles
            disableRotation={false}
            moveParticlesOnHover
            particleHoverFactor={0.6}
          />
        </div>
        <div className="hero-content">
          <h1>
            Know your data <span className="gradient-text">before</span> you model it.
          </h1>
          <p className="lede">
            Upload a raw dataset and AutoML analyzes it, explains what's wrong with it in plain
            English, suggests fixes with real reasoning, and tells you which algorithm to try
            next. Built for students, researchers, and anyone new to machine learning.
          </p>
          <div className="hero-actions">
            <Link to="/workspace" className="btn btn-primary">
              Get started →
            </Link>
            <a href="#how-it-works" className="btn btn-secondary">
              See how it works
            </a>
          </div>
        </div>
        <GradualBlur target="parent" position="bottom" height="5rem" strength={1.5} divCount={4} curve="bezier" opacity={0.9} />
      </section>

      <div className="stats-strip">
        <div className="stat">
          <div className="stat-value">4</div>
          <div className="stat-caption">Pipeline stages</div>
        </div>
        <div className="stat">
          <div className="stat-value">0</div>
          <div className="stat-caption">Black-box suggestions</div>
        </div>
        <div className="stat">
          <div className="stat-value">100%</div>
          <div className="stat-caption">Reasoning shown</div>
        </div>
      </div>

      <section id="how-it-works" className="site-section">
        <span className="section-kicker">The pipeline</span>
        <h2>Four stages. One upload.</h2>
        <div className="feature-grid">
          {STEPS.map((step) => (
            <GlowCard key={step.n}>
              <span className="step-number">{step.n}</span>
              <h3>{step.title}</h3>
              <p>{step.body}</p>
            </GlowCard>
          ))}
        </div>
      </section>

      <section id="who-its-for" className="site-section">
        <span className="section-kicker">Who it's for</span>
        <h2>No data science degree required.</h2>
        <div className="feature-grid">
          {AUDIENCES.map((a) => (
            <GlowCard key={a.title}>
              <h3>{a.title}</h3>
              <p>{a.body}</p>
            </GlowCard>
          ))}
        </div>
      </section>

      <section id="deliverables" className="site-section">
        <span className="section-kicker">What you get</span>
        <h2>Every stage hands you something concrete.</h2>
        <div className="feature-grid">
          {DELIVERABLES.map((d) => (
            <GlowCard key={d.title}>
              <h3>{d.title}</h3>
              <p>{d.body}</p>
            </GlowCard>
          ))}
        </div>
      </section>

      <section id="about" className="site-section site-section-blurred" style={{ textAlign: "center" }}>
        <span className="section-kicker">About</span>
        <h2 style={{ maxWidth: "18ch", margin: "8px auto 0" }}>
          Explains its reasoning. Uses real AutoML. Ends with a next step.
        </h2>
        <p style={{ maxWidth: "60ch", margin: "20px auto 0", fontSize: 16 }}>
          Most tools either automate preprocessing as a black box, or leave you to do it by
          hand with no guidance. AutoML does neither: every suggestion is grounded in an
          actual statistic from your data, and the pipeline ends with a ranked algorithm
          shortlist, not just a clean CSV and nothing else.
        </p>
        <GradualBlur target="parent" position="bottom" height="6rem" strength={2} divCount={5} curve="bezier" animated="scroll" duration="0.6s" />
        <GradualBlur target="parent" position="top" height="4rem" strength={1.2} divCount={4} curve="bezier" animated="scroll" duration="0.6s" />
      </section>

      <footer className="site-footer">
        <div className="site-footer-top">
          <span>AutoML, built for people who'd rather understand their data than fight it.</span>
          <span>Local-first · No account needed</span>
        </div>
        <div className="site-footer-legal">
          {"©"} {new Date().getFullYear()} Ragini Pawar. All rights reserved. This design, its
          layout, and its source code are original work and may not be copied, cloned, or
          reproduced without permission.
        </div>
      </footer>
    </div>
  );
}
