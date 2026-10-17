import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { experimentsApi } from "../api/experiments";
import { PageHeader } from "../components/ui/PageHeader";
import { Button } from "../components/ui/Button";
import { Card, CardBody } from "../components/ui/Card";
import { EmptyState } from "../components/ui/EmptyState";
import { SkeletonCard } from "../components/ui/Skeleton";
import "./Dashboard.css";

export function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["experiments"],
    queryFn: experimentsApi.list,
  });

  const stats = data
    ? {
        experiments: data.length,
        personas: data.reduce((sum, e) => sum + e.personaCount, 0),
        surveys: data.reduce((sum, e) => sum + e.surveyCount, 0),
      }
    : null;

  return (
    <div>
      <PageHeader
        title="Research dashboard"
        subtitle="Create studies, generate synthetic personas, and run surveys or interviews to validate product ideas."
        actions={
          <>
            <Link to="/scenarios">
              <Button variant="secondary">Browse sample scenarios</Button>
            </Link>
            <Link to="/experiments/new">
              <Button variant="primary">New experiment</Button>
            </Link>
          </>
        }
      />

      {stats && (
        <div className="dashboard-stats">
          <Card>
            <CardBody>
              <div className="stat-value">{stats.experiments}</div>
              <div className="stat-label">Experiments</div>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <div className="stat-value">{stats.personas}</div>
              <div className="stat-label">Synthetic personas</div>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <div className="stat-value">{stats.surveys}</div>
              <div className="stat-label">Surveys run</div>
            </CardBody>
          </Card>
        </div>
      )}

      <h2 className="dashboard-section-title">Recent studies</h2>

      {isLoading && (
        <div className="dashboard-grid">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {error && (
        <EmptyState title="Could not load experiments" description="Check that the backend API is running and reachable." />
      )}

      {data && data.length === 0 && (
        <EmptyState
          icon="✦"
          title="No experiments yet"
          description="Start a new research experiment, or launch a ready-made sample scenario to see the platform in action."
          action={
            <Link to="/experiments/new">
              <Button variant="primary">Create your first experiment</Button>
            </Link>
          }
        />
      )}

      {data && data.length > 0 && (
        <div className="dashboard-grid">
          {data.map((exp) => (
            <Link key={exp.id} to={`/experiments/${exp.id}`} className="dashboard-card-link">
              <Card className="card-interactive">
                <CardBody>
                  <div className="dashboard-card-title">{exp.name}</div>
                  <p className="dashboard-card-desc">{exp.productDescription}</p>
                  <div className="dashboard-card-meta">
                    <span>{exp.personaCount} personas</span>
                    <span>·</span>
                    <span>{exp.surveyCount} surveys</span>
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
