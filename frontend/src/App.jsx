import { BrowserRouter, Outlet, Route, Routes } from "react-router-dom";
import { PipelineProvider } from "./context/PipelineContext";
import { ThemeProvider } from "./context/ThemeContext";
import NavBar from "./components/NavBar";
import StepperNav from "./components/StepperNav";
import HomePage from "./pages/HomePage";
import UploadPage from "./pages/UploadPage";
import AnalysisPage from "./pages/AnalysisPage";
import SuggestionsPage from "./pages/SuggestionsPage";
import ApplyExportPage from "./pages/ApplyExportPage";
import ValidationAccuracyPage from "./pages/ValidationAccuracyPage";
import RecommendationsPage from "./pages/RecommendationsPage";

function WizardLayout() {
  return (
    <div>
      <NavBar />
      <div className="app-shell">
        <StepperNav />
        <Outlet />
      </div>
      <div className="site-footer-legal" style={{ padding: "0 24px 24px" }}>
        {"©"} {new Date().getFullYear()} Ragini Pawar. All rights reserved. This design, its
        layout, and its source code are original work and may not be copied, cloned, or reproduced
        without permission.
      </div>
    </div>
  );
}

export default function App() {
  return (
    <ThemeProvider>
      <PipelineProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/workspace" element={<WizardLayout />}>
              <Route index element={<UploadPage />} />
              <Route path="analysis" element={<AnalysisPage />} />
              <Route path="suggestions" element={<SuggestionsPage />} />
              <Route path="apply" element={<ApplyExportPage />} />
              <Route path="validation" element={<ValidationAccuracyPage />} />
              <Route path="recommend" element={<RecommendationsPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </PipelineProvider>
    </ThemeProvider>
  );
}
