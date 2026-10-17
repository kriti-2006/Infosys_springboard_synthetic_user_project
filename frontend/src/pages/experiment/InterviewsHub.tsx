import { useNavigate, useOutletContext } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ExperimentContext } from "./ExperimentLayout";
import { interviewsApi } from "../../api/interviews";
import { errorMessage } from "../../api/client";
import { PersonaCard } from "../../components/personas/PersonaCard";
import { Card, CardBody } from "../../components/ui/Card";
import { EmptyState } from "../../components/ui/EmptyState";
import { StatusBadge } from "../../components/ui/Badge";
import { useToast } from "../../components/ui/Toast";
import "./InterviewsHub.css";

export function InterviewsHub() {
  const { experiment, personas } = useOutletContext<ExperimentContext>();
  const navigate = useNavigate();
  const toast = useToast();
  const queryClient = useQueryClient();

  const interviewsQuery = useQuery({
    queryKey: ["interviews", experiment.id],
    queryFn: () => interviewsApi.listByExperiment(experiment.id),
  });

  const startInterview = useMutation({
    mutationFn: (personaId: string) => interviewsApi.create(experiment.id, personaId),
    onSuccess: (iv) => {
      queryClient.invalidateQueries({ queryKey: ["interviews", experiment.id] });
      navigate(`/experiments/${experiment.id}/interviews/${iv.id}`);
    },
    onError: (err) => toast.show(errorMessage(err), "error"),
  });

  if (personas.length === 0) {
    return <EmptyState title="Generate personas first" description="Interviews require at least one persona to talk to." />;
  }

  return (
    <div>
      <h3 className="interviews-hub-section-title">Start a new interview</h3>
      <div className="interviews-hub-grid">
        {personas.map((p) => (
          <PersonaCard key={p.id} persona={p} onClick={() => startInterview.mutate(p.id)} />
        ))}
      </div>

      {interviewsQuery.data && interviewsQuery.data.length > 0 && (
        <>
          <h3 className="interviews-hub-section-title" style={{ marginTop: 32 }}>
            Past interviews
          </h3>
          <div className="interviews-hub-list">
            {interviewsQuery.data.map((iv) => (
              <Card
                key={iv.id}
                className="card-interactive"
                onClick={() => navigate(`/experiments/${experiment.id}/interviews/${iv.id}`)}
                style={{ cursor: "pointer" }}
              >
                <CardBody className="interviews-hub-list-item">
                  <span>{iv.personaName ?? "Unknown persona"}</span>
                  <StatusBadge status={iv.status} />
                </CardBody>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
