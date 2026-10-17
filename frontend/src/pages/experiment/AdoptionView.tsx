import { useState } from "react";
import { useOutletContext } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ExperimentContext } from "./ExperimentLayout";
import { analysisApi } from "../../api/analysis";
import { errorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonCard } from "../../components/ui/Skeleton";
import { Badge, SegmentBadge } from "../../components/ui/Badge";
import { AdoptionMeter } from "../../components/charts/AdoptionMeter";
import { useToast } from "../../components/ui/Toast";
import "./AdoptionView.css";

const DECISION_TONE: Record<string, "positive" | "negative" | "neutral" | "mixed"> = {
  very_likely: "positive",
  likely: "positive",
  neutral: "neutral",
  unlikely: "negative",
  very_unlikely: "negative",
};

export function AdoptionView() {
  const { experiment, personas } = useOutletContext<ExperimentContext>();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState<string | null>(null);

  const scoresQuery = useQuery({
    queryKey: ["usage-scores", experiment.id],
    queryFn: () => analysisApi.getUsageScores(experiment.id),
  });

  const run = useMutation({
    mutationFn: () => analysisApi.scoreUsage(experiment.id),
    onSuccess: (res) => {
      if (res.scores.length === 0 && res.failed.length > 0) {
        toast.show(`Scoring failed for all ${res.failed.length} personas: ${res.failed[0].error}`, "error");
      } else if (res.failed.length > 0) {
        toast.show(`Scored ${res.scores.length} personas, ${res.failed.length} failed`, "info");
      } else {
        toast.show(`Scored ${res.scores.length} personas`, "success");
      }
      queryClient.invalidateQueries({ queryKey: ["usage-scores", experiment.id] });
    },
    onError: (err) => toast.show(errorMessage(err), "error"),
  });

  const data = scoresQuery.data;
  const sorted = data ? [...data.scores].sort((a, b) => b.score - a.score) : [];

  return (
    <div>
      <Card style={{ marginBottom: 24 }}>
        <CardHeader>
          <div>
            <strong>Would they use this product?</strong>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
              A transparent 0-100 adoption likelihood per persona, grounded in their attributes and actual prior answers — a synthetic
              research estimate, not a real-world market prediction.
            </div>
          </div>
          <Button onClick={() => run.mutate()} loading={run.isPending} disabled={personas.length === 0}>
            {data && data.scores.length > 0 ? "Re-score all personas" : "Score personas"}
          </Button>
        </CardHeader>
      </Card>

      {scoresQuery.isLoading && <SkeletonCard />}

      {data && data.scores.length === 0 && (
        <EmptyState
          icon="◉"
          title="No adoption scores yet"
          description="Score every persona to see an overall likelihood, a breakdown by segment, and the reasoning behind each score."
        />
      )}

      {data && data.scores.length > 0 && (
        <>
          <div className="adoption-overview">
            <Card>
              <CardBody>
                <div className="adoption-overview-label">Overall likelihood</div>
                <AdoptionMeter score={data.overallLikelihood ?? 0} size="lg" />
                <div className="adoption-overview-footnote">
                  based on {data.scores.length} persona{data.scores.length === 1 ? "" : "s"}
                </div>
              </CardBody>
            </Card>
            {Object.entries(data.bySegment).map(([segment, s]) => (
              <Card key={segment}>
                <CardBody>
                  <div className="adoption-overview-label">{segment.replace("_", " ")}</div>
                  <AdoptionMeter score={s.likelihood} />
                  <div className="adoption-overview-footnote">{s.personas} personas</div>
                </CardBody>
              </Card>
            ))}
          </div>

          <h3 className="adoption-section-title">By persona</h3>
          <div className="adoption-persona-list">
            {sorted.map((s) => (
              <Card key={s.personaId}>
                <CardBody>
                  <div className="adoption-row" onClick={() => setExpanded(expanded === s.personaId ? null : s.personaId)}>
                    <div className="adoption-row-identity">
                      <div className="adoption-row-name">{s.personaName}</div>
                      <SegmentBadge segment={s.segment} />
                    </div>
                    <div className="adoption-row-meter">
                      <AdoptionMeter score={s.score} />
                    </div>
                    <Badge tone={DECISION_TONE[s.decision] ?? "navy"}>{s.decision.replace("_", " ")}</Badge>
                  </div>
                  {expanded === s.personaId && (
                    <div className="adoption-row-detail">
                      <p>{s.reasoning}</p>
                      {s.factors && s.factors.length > 0 && (
                        <ul className="adoption-factor-list">
                          {s.factors.map((f, i) => (
                            <li key={i} className={f.impact === "positive" ? "adoption-factor-positive" : "adoption-factor-negative"}>
                              {f.impact === "positive" ? "+" : "−"} {f.factor}
                            </li>
                          ))}
                        </ul>
                      )}
                      <div className="adoption-row-confidence">confidence: {Math.round(s.confidence * 100)}%</div>
                    </div>
                  )}
                </CardBody>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
