import { Route, Routes } from "react-router-dom";
import { AppShell } from "./components/layout/AppShell";
import { Dashboard } from "./pages/Dashboard";
import { ExperimentNew } from "./pages/ExperimentNew";
import { ExperimentLayout } from "./pages/experiment/ExperimentLayout";
import { ExperimentOverview } from "./pages/experiment/ExperimentOverview";
import { SurveysList } from "./pages/experiment/SurveysList";
import { SurveyNew } from "./pages/experiment/SurveyNew";
import { SurveyDetail } from "./pages/experiment/SurveyDetail";
import { SurveyResultsPage } from "./pages/experiment/SurveyResultsPage";
import { InterviewsHub } from "./pages/experiment/InterviewsHub";
import { InterviewChat } from "./pages/experiment/InterviewChat";
import { InsightsView } from "./pages/experiment/InsightsView";
import { AdoptionView } from "./pages/experiment/AdoptionView";
import { ScenariosGallery } from "./pages/ScenariosGallery";
import { NotFound } from "./pages/NotFound";

function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Dashboard />} />
        <Route path="scenarios" element={<ScenariosGallery />} />
        <Route path="experiments/new" element={<ExperimentNew />} />
        <Route path="experiments/:experimentId" element={<ExperimentLayout />}>
          <Route index element={<ExperimentOverview />} />
          <Route path="surveys" element={<SurveysList />} />
          <Route path="surveys/new" element={<SurveyNew />} />
          <Route path="surveys/:surveyId" element={<SurveyDetail />} />
          <Route path="surveys/:surveyId/results" element={<SurveyResultsPage />} />
          <Route path="interviews" element={<InterviewsHub />} />
          <Route path="interviews/:interviewId" element={<InterviewChat />} />
          <Route path="insights" element={<InsightsView />} />
          <Route path="adoption" element={<AdoptionView />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

export default App;
