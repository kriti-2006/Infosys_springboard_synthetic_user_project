import { Link, useOutletContext } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import type { ExperimentContext } from "./ExperimentLayout";
import { surveysApi } from "../../api/surveys";
import { Button } from "../../components/ui/Button";
import { Card, CardBody } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonCard } from "../../components/ui/Skeleton";
import { StatusBadge } from "../../components/ui/Badge";
import "./SurveysList.css";

export function SurveysList() {
  const { experiment } = useOutletContext<ExperimentContext>();
  const { data, isLoading } = useQuery({
    queryKey: ["surveys", experiment.id],
    queryFn: () => surveysApi.listByExperiment(experiment.id),
  });

  return (
    <div>
      <div className="surveys-list-toolbar">
        <h2>Surveys</h2>
        <Link to={`/experiments/${experiment.id}/surveys/new`}>
          <Button>New survey</Button>
        </Link>
      </div>

      {isLoading && (
        <div className="surveys-list-grid">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {data && data.length === 0 && (
        <EmptyState
          icon="▤"
          title="No surveys yet"
          description="Create a survey with open-ended, multiple-choice, rating, or yes/no questions and run it across your personas concurrently."
          action={
            <Link to={`/experiments/${experiment.id}/surveys/new`}>
              <Button>Create a survey</Button>
            </Link>
          }
        />
      )}

      {data && data.length > 0 && (
        <div className="surveys-list-grid">
          {data.map((survey) => (
            <Link key={survey.id} to={`/experiments/${experiment.id}/surveys/${survey.id}`}>
              <Card className="card-interactive">
                <CardBody>
                  <div className="survey-card-top">
                    <div className="survey-card-title">{survey.title}</div>
                    <StatusBadge status={survey.status} />
                  </div>
                  <div className="survey-card-meta">
                    {survey.questions.length} questions · {survey.personaIds.length} personas
                  </div>
                  <div className="survey-card-progress">
                    {survey.progress.completed}/{survey.progress.expected} responses
                    {survey.progress.failed > 0 && <span className="survey-card-failed"> · {survey.progress.failed} failed</span>}
                  </div>
                </CardBody>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
