import { Link, useOutletContext, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ExperimentContext } from "./ExperimentLayout";
import { surveysApi } from "../../api/surveys";
import { errorMessage } from "../../api/client";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { StatusBadge } from "../../components/ui/Badge";
import { SkeletonCard } from "../../components/ui/Skeleton";
import { useToast } from "../../components/ui/Toast";
import "./SurveyDetail.css";

export function SurveyDetail() {
  const { experiment } = useOutletContext<ExperimentContext>();
  const { surveyId } = useParams<{ surveyId: string }>();
  const toast = useToast();
  const queryClient = useQueryClient();

  const surveyQuery = useQuery({
    queryKey: ["survey", surveyId],
    queryFn: () => surveysApi.get(surveyId!),
    enabled: !!surveyId,
    refetchInterval: (query) => (query.state.data?.status === "running" ? 2000 : false),
  });

  const run = useMutation({
    mutationFn: () => surveysApi.run(surveyId!),
    onSuccess: () => {
      toast.show("Survey started", "info");
      queryClient.invalidateQueries({ queryKey: ["survey", surveyId] });
    },
    onError: (err) => toast.show(errorMessage(err), "error"),
  });

  if (surveyQuery.isLoading) return <SkeletonCard />;
  if (!surveyQuery.data) return null;
  const survey = surveyQuery.data;
  const pct = survey.progress.expected > 0 ? Math.round((100 * survey.progress.completed) / survey.progress.expected) : 0;
  const canRun = survey.status === "draft" || survey.status === "partial" || survey.status === "failed";

  return (
    <div>
      <Card style={{ marginBottom: 20 }}>
        <CardHeader>
          <div>
            <div className="survey-detail-title">{survey.title}</div>
            <div className="survey-detail-meta">
              {survey.questions.length} questions · {survey.personaIds.length} personas
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <StatusBadge status={survey.status} />
            {canRun && (
              <Button onClick={() => run.mutate()} loading={run.isPending}>
                {survey.status === "draft" ? "Run survey" : "Resume"}
              </Button>
            )}
            {(survey.status === "completed" || survey.progress.completed > 0) && (
              <Link to={`/experiments/${experiment.id}/surveys/${survey.id}/results`}>
                <Button variant="secondary">View results</Button>
              </Link>
            )}
          </div>
        </CardHeader>
        <CardBody>
          {survey.researchObjective && <p className="survey-detail-objective">{survey.researchObjective}</p>}
          <div className="survey-progress-bar">
            <div className="survey-progress-fill" style={{ width: `${pct}%` }} />
          </div>
          <div className="survey-progress-label">
            {survey.progress.completed} / {survey.progress.expected} responses
            {survey.progress.failed > 0 && <span className="survey-progress-failed"> · {survey.progress.failed} failed</span>}
            {survey.status === "running" && <span className="survey-progress-live"> · generating live…</span>}
          </div>
        </CardBody>
      </Card>

      <h3 className="survey-detail-section-title">Questions</h3>
      <div className="survey-detail-questions">
        {survey.questions.map((q, i) => (
          <div key={q.id} className="survey-detail-question">
            <span className="survey-detail-question-number">Q{i + 1}</span>
            <div>
              <div>{q.question}</div>
              <div className="survey-detail-question-type">
                {q.type.replace("_", " ")}
                {q.options && q.options.length > 0 && ` · ${q.options.join(", ")}`}
                {q.type === "rating" && ` · ${q.scaleMin}-${q.scaleMax}`}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
