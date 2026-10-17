import { Link } from "react-router-dom";
import { EmptyState } from "../components/ui/EmptyState";
import { Button } from "../components/ui/Button";

export function NotFound() {
  return (
    <EmptyState
      title="Page not found"
      description="The page you're looking for doesn't exist or has moved."
      action={
        <Link to="/">
          <Button variant="secondary">Back to dashboard</Button>
        </Link>
      }
    />
  );
}
