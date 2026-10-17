import { useState } from "react";
import { useOutletContext, Link, useLocation } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import type { ExperimentContext } from "./ExperimentLayout";
import { experimentsApi } from "../../api/experiments";
import { errorMessage } from "../../api/client";
import type { SuggestedQuestion } from "../../api/scenarios";
import { Button } from "../../components/ui/Button";
import { Card, CardBody, CardHeader } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { SkeletonCard } from "../../components/ui/Skeleton";
import { PersonaCard } from "../../components/personas/PersonaCard";
import { FieldShell, Select } from "../../components/ui/Field";
import { useToast } from "../../components/ui/Toast";
import "./ExperimentOverview.css";

export function ExperimentOverview() {
  const { experiment, personas, personasLoading } = useOutletContext<ExperimentContext>();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [count, setCount] = useState(5);
  const location = useLocation();
  const suggestedQuestions = (location.state as { suggestedQuestions?: SuggestedQuestion[] } | null)?.suggestedQuestions;

  const generate = useMutation({
    mutationFn: () => experimentsApi.generatePersonas(experiment.id, count),
    onSuccess: (newPersonas) => {
      toast.show(`Generated ${newPersonas.length} personas`, "success");
      queryClient.invalidateQueries({ queryKey: ["personas", experiment.id] });
      queryClient.invalidateQueries({ queryKey: ["experiments"] });
    },
    onError: (err) => toast.show(errorMessage(err), "error"),
  });

  return (
    <div>
      {suggestedQuestions && suggestedQuestions.length > 0 && (
        <Card style={{ marginBottom: 24, borderColor: "var(--accent-violet)" }}>
          <CardBody style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 16, flexWrap: "wrap" }}>
            <div>
              <strong>Sample scenario launched</strong>
              <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
                Generate personas below, then create the suggested survey to try the full flow.
              </div>
            </div>
            <Link to={`/experiments/${experiment.id}/surveys/new`} state={{ suggestedQuestions }}>
              <Button variant="secondary">Use suggested survey ({suggestedQuestions.length} questions)</Button>
            </Link>
          </CardBody>
        </Card>
      )}
      <Card style={{ marginBottom: 24 }}>
        <CardHeader>
          <div>
            <strong>Personas</strong>
            <div style={{ fontSize: 13, color: "var(--text-secondary)", marginTop: 2 }}>
              Generated once per experiment, then reused consistently across every survey and interview.
            </div>
          </div>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <FieldShell>
              <Select value={count} onChange={(e) => setCount(Number(e.target.value))} style={{ minWidth: 110 }}>
                {[3, 5, 8, 10, 15, 20].map((n) => (
                  <option key={n} value={n}>
                    {n} personas
                  </option>
                ))}
              </Select>
            </FieldShell>
            <Button onClick={() => generate.mutate()} loading={generate.isPending}>
              {personas.length > 0 ? "Generate more" : "Generate personas"}
            </Button>
          </div>
        </CardHeader>
      </Card>

      {personasLoading && (
        <div className="overview-persona-grid">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {!personasLoading && personas.length === 0 && (
        <EmptyState
          icon="◎"
          title="No personas yet"
          description="Generate a set of diverse synthetic personas grounded in the product description and target audience above."
          action={<Button onClick={() => generate.mutate()} loading={generate.isPending}>Generate personas</Button>}
        />
      )}

      {personas.length > 0 && (
        <>
          <div className="overview-persona-grid">
            {personas.map((p) => (
              <PersonaCard key={p.id} persona={p} />
            ))}
          </div>
          <div className="overview-next-steps">
            <Link to={`/experiments/${experiment.id}/surveys/new`}>
              <Button variant="secondary">Run a survey →</Button>
            </Link>
            <Link to={`/experiments/${experiment.id}/interviews`}>
              <Button variant="secondary">Start an interview →</Button>
            </Link>
          </div>
        </>
      )}
    </div>
  );
}
