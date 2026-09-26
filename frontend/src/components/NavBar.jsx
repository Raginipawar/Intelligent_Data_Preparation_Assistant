// Copyright (c) Ragini Pawar. All rights reserved.
// Original design and source — not to be copied, cloned, or reproduced without permission.
import { Link } from "react-router-dom";
import { useTheme } from "../context/ThemeContext";

const NAV_LINKS = [
  { href: "/#how-it-works", label: "How it works" },
  { href: "/#who-its-for", label: "Who it's for" },
  { href: "/#deliverables", label: "Deliverables" },
  { href: "/#about", label: "About" },
];

export default function NavBar() {
  const { theme, toggleTheme } = useTheme();

  return (
    <nav className="site-nav">
      <Link to="/" className="logo">
        AutoML
      </Link>
      <div className="nav-links">
        {NAV_LINKS.map((link) => (
          <Link key={link.href} to={link.href}>
            {link.label}
          </Link>
        ))}
        <button
          className="theme-toggle"
          onClick={toggleTheme}
          aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
          title={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
        >
          {theme === "dark" ? "☀" : "☾"}
        </button>
        <Link to="/workspace" className="btn btn-primary" style={{ padding: "8px 16px" }}>
          Get started →
        </Link>
      </div>
    </nav>
  );
}
