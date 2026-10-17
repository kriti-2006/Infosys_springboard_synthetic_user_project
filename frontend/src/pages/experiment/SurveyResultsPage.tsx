import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { surveysApi } from "../../api/surveys";
import { SkeletonCard } from "../../components/ui/Skeleton";
import { EmptyState } from "../../components/ui/EmptyState";
import { Card, CardBody } from "../../components/ui/Card";
import { SegmentBadge, SentimentBadge } from "../../components/ui/Badge";
import "./SurveyResultsPage.css";

function formatValue(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  if (Array.isArray(value)) return value.join(", ");
  if (typeof value === "boolean") return value ? "Yes" : "No";
  return String(value);
}

export function SurveyResultsPage() {
  const { surveyId } = useParams<{ surveyId: string }>();
  const resultsQuery = useQuery({
    queryKey: ["survey-results", surveyId],
    queryFn: () => surveysApi.results(surveyId!),
    enabled: !!surveyId,
  });
  const surveyQuery = useQuery({
    queryKey: ["survey", surveyId],
    queryFn: () => surveysApi.get(surveyId!),
    enabled: !!surveyId,
  });

  if (resultsQuery.isLoading || surveyQuery.isLoading) return <SkeletonCard />;
  const data = resultsQuery.data;
  const survey = surveyQuery.data;
  if (!data || !survey) return null;

  if (data.personas.every((p) => p.responses.length === 0)) {
    return <EmptyState title="No completed responses yet" description="Run the survey, then come back here to compare answers." />;
  }

  const questions = survey.questions.map((q) => ({ id: q.questionId, text: q.question }));
  const byPersonaQuestion = new Map<string, (typeof data.personas)[0]["responses"][0]>();
  for (const persona of data.personas) {
    for (const r of persona.responses) {
      byPersonaQuestion.set(`${persona.personaId}:${r.questionId}`, r);
    }
  }

  return (
    <div>
      <div className="results-summary">
        <Card>
          <CardBody>
            <div className="results-stat">{data.survey.progress.completed}</div>
            <div className="results-stat-label">Completed responses</div>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <div className="results-stat">{data.personas.length}</div>
            <div className="results-stat-label">Personas</div>
          </CardBody>
        </Card>
        {data.failures.length > 0 && (
          <Card>
            <CardBody>
              <div className="results-stat results-stat-danger">{data.failures.length}</div>
              <div className="results-stat-label">Failed cells</div>
            </CardBody>
          </Card>
        )}
      </div>

      <div className="results-table-scroll">
        <table className="results-table">
          <thead>
            <tr>
              <th className="results-table-question-col">Question</th>
              {data.personas.map((p) => (
                <th key={p.personaId}>
                  <div className="results-persona-head">
                    <div className="results-persona-name">{p.name ?? "Unknown"}</div>
                    <SegmentBadge segment={p.segment} />
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {questions.map((q) => (
              <tr key={q.id}>
                <td className="results-table-question-col">{q.text}</td>
                {data.personas.map((p) => {
                  const r = byPersonaQuestion.get(`${p.personaId}:${q.id}`);
                  const typed = formatValue(r?.value);
                  return (
                    <td key={p.personaId} className={r?.flagged ? "results-cell-flagged" : undefined}>
                      {r ? (
                        <div className="results-cell">
                          <div className="results-cell-text">{r.response}</div>
                          {typed && <div className="results-cell-value">{typed}</div>}
                          <div className="results-cell-meta">
                            <SentimentBadge sentiment={r.sentiment} />
                            {r.flagged && <span className="results-cell-flag-label">flagged</span>}
                          </div>
                        </div>
                      ) : (
                        <span className="results-cell-empty">—</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {data.failures.length > 0 && (
        <div className="results-failures">
          <h3>Failed cells</h3>
          <ul>
            {data.failures.map((f, i) => (
              <li key={i}>
                Persona {f.personaId.slice(0, 8)} · {f.questionId}: {f.error ?? "unknown error"}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
