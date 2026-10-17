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
import { SentimentBadge } from "../../components/ui/Badge";
import { SentimentBar } from "../../components/charts/SentimentBar";
import { FieldShell, Select } from "../../components/ui/Field";
import { useToast } from "../../components/ui/Toast";
import "./InsightsView.css";

export function InsightsView() {
  const { experiment } = useOutletContext<ExperimentContext>();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [source, setSource] = useState<"combined" | "survey" | "interview">("combined");

  const listQuery = useQuery({
    queryKey: ["insights", experiment.id],
    queryFn: () => analysisApi.listInsights(experiment.id),
  });

  const extract = useMutation({
    mutationFn: () => analysisApi.createInsights(experiment.id, source),
    onSuccess: () => {
      toast.show("Insights extracted", "success");
      queryClient.invalidateQueries({ queryKey: ["insights", experiment.id] });
    },
    onError: (err) => toast.show(errorMessage(err), "error"),
  });

  const latest = listQuery.data?.[0];

  return (
    <div>
      <Card style={{ marginBottom: 24 }}>
        <CardHeader>
          <div>
            <strong>Insight extraction</strong>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
              Themes, sentiment, agreement and contradictions — grounded only in real responses. Every statistic is computed, never
              invented.
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <FieldShell>
              <Select value={source} onChange={(e) => setSource(e.target.value as typeof source)} style={{ minWidth: 150 }}>
                <option value="combined">Survey + interviews</option>
                <option value="survey">Survey only</option>
                <option value="interview">Interviews only</option>
              </Select>
            </FieldShell>
            <Button onClick={() => extract.mutate()} loading={extract.isPending}>
              Extract insights
            </Button>
          </div>
        </CardHeader>
      </Card>

      {listQuery.isLoading && <SkeletonCard />}

      {!listQuery.isLoading && !latest && (
        <EmptyState
          icon="◈"
          title="No insights yet"
          description="Run a survey or interview first, then extract insights to see themes, sentiment and contradictions across your personas."
        />
      )}

      {latest && (
        <>
          <div className="insights-meta">
            {latest.data.participants} participants · {latest.data.responsesAnalysed} responses analysed · extracted{" "}
            {new Date(latest.createdAt).toLocaleString()}
          </div>

          <Card style={{ marginBottom: 24 }}>
            <CardHeader>
              <strong>Overall sentiment</strong>
            </CardHeader>
            <CardBody>
              <SentimentBar data={latest.data.sentiment} />
            </CardBody>
          </Card>

          {Object.keys(latest.data.segmentSentiment).length > 0 && (
            <Card style={{ marginBottom: 24 }}>
              <CardHeader>
                <strong>Sentiment by segment</strong>
              </CardHeader>
              <CardBody style={{ display: "flex", flexDirection: "column", gap: 16 }}>
                {Object.entries(latest.data.segmentSentiment).map(([segment, dist]) => (
                  <div key={segment}>
                    <div className="insights-segment-label">{segment.replace("_", " ")}</div>
                    <SentimentBar data={dist} compact />
                  </div>
                ))}
              </CardBody>
            </Card>
          )}

          <h3 className="insights-section-title">Themes</h3>
          <div className="insights-themes">
            {latest.data.themes.map((theme) => (
              <Card key={theme.name}>
                <CardBody>
                  <div className="insights-theme-head">
                    <div className="insights-theme-name">{theme.name}</div>
                    <SentimentBadge sentiment={theme.sentiment} />
                  </div>
                  <p className="insights-theme-desc">{theme.description}</p>
                  <div className="insights-theme-freq">
                    {theme.frequency} of {latest.data.participants} personas ({theme.percentage}%)
                  </div>
                  {theme.evidence.length > 0 && (
                    <div className="insights-evidence">
                      {theme.evidence.map((e, i) => (
                        <div key={i} className="insights-evidence-item">
                          "{e.excerpt}"
                        </div>
                      ))}
                    </div>
                  )}
                </CardBody>
              </Card>
            ))}
          </div>

          {latest.data.agreementPatterns.length > 0 && (
            <>
              <h3 className="insights-section-title">Agreement patterns</h3>
              <ul className="insights-list">
                {latest.data.agreementPatterns.map((a, i) => (
                  <li key={i}>{a.summary}</li>
                ))}
              </ul>
            </>
          )}

          {latest.data.behavioralTrends.length > 0 && (
            <>
              <h3 className="insights-section-title">Behavioral trends</h3>
              <ul className="insights-list">
                {latest.data.behavioralTrends.map((t, i) => (
                  <li key={i}>
                    {t.trend}
                    {t.segments.length > 0 && <span className="insights-list-tag"> · {t.segments.join(", ")}</span>}
                  </li>
                ))}
              </ul>
            </>
          )}

          {latest.data.contradictions.length > 0 && (
            <>
              <h3 className="insights-section-title">Contradictions</h3>
              <div className="insights-contradictions">
                {latest.data.contradictions.map((c, i) => (
                  <Card key={i}>
                    <CardBody>
                      <div className="insights-theme-name">{c.topic}</div>
                      <div className="insights-contradiction-positions">
                        {c.positions.map((p, pi) => (
                          <div key={pi} className="insights-contradiction-position">
                            <span className="insights-contradiction-dot" />
                            {p.stance} ({p.personaIds.length})
                          </div>
                        ))}
                      </div>
                    </CardBody>
                  </Card>
                ))}
              </div>
            </>
          )}

          {latest.data.outliers.length > 0 && (
            <>
              <h3 className="insights-section-title">Outliers</h3>
              <ul className="insights-list">
                {latest.data.outliers.map((o, i) => (
                  <li key={i}>{o.reason}</li>
                ))}
              </ul>
            </>
          )}
        </>
      )}
    </div>
  );
}
