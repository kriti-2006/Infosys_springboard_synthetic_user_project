import { Link, Outlet, useLocation, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { experimentsApi } from "../../api/experiments";
import type { Experiment, Persona } from "../../api/types";
import { PageHeader } from "../../components/ui/PageHeader";
import { Tabs } from "../../components/ui/Tabs";
import { SkeletonCard } from "../../components/ui/Skeleton";
import { EmptyState } from "../../components/ui/EmptyState";

export interface ExperimentContext {
  experiment: Experiment;
  personas: Persona[];
  personasLoading: boolean;
}

const TABS = [
  { key: "", label: "Overview" },
  { key: "surveys", label: "Surveys" },
  { key: "interviews", label: "Interviews" },
  { key: "insights", label: "Insights" },
  { key: "adoption", label: "Adoption score" },
];

export function ExperimentLayout() {
  const { experimentId } = useParams<{ experimentId: string }>();
  const navigate = useNavigate();
  const location = useLocation();

  const experimentQuery = useQuery({
    queryKey: ["experiment", experimentId],
    queryFn: () => experimentsApi.get(experimentId!),
    enabled: !!experimentId,
  });

  const personasQuery = useQuery({
    queryKey: ["personas", experimentId],
    queryFn: () => experimentsApi.listPersonas(experimentId!),
    enabled: !!experimentId,
  });

  if (experimentQuery.isLoading) {
    return <SkeletonCard />;
  }

  if (experimentQuery.error || !experimentQuery.data) {
    return <EmptyState title="Experiment not found" description="It may have been removed, or the link is incorrect." />;
  }

  const experiment = experimentQuery.data;
  const base = `/experiments/${experimentId}`;
  const segments = location.pathname.replace(base, "").split("/").filter(Boolean);
  const activeTab = segments[0] ?? "";

  const ctx: ExperimentContext = {
    experiment,
    personas: personasQuery.data ?? [],
    personasLoading: personasQuery.isLoading,
  };

  return (
    <div>
      <PageHeader
        title={
          <>
            <Link to="/" style={{ color: "var(--text-muted)", fontSize: 13, fontWeight: 600 }}>
              Dashboard
            </Link>
            <span style={{ color: "var(--text-muted)", margin: "0 6px" }}>/</span>
            {experiment.name}
          </>
        }
        subtitle={experiment.productDescription}
      />
      <Tabs items={TABS} active={activeTab} onChange={(key) => navigate(key ? `${base}/${key}` : base)} />
      <Outlet context={ctx} />
    </div>
  );
}
