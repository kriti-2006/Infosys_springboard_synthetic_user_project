import "./Skeleton.css";

export function Skeleton({ width, height = 14 }: { width?: string | number; height?: string | number }) {
  return <span className="skeleton" style={{ width, height }} />;
}

export function SkeletonCard() {
  return (
    <div className="skeleton-card">
      <Skeleton width="40%" height={16} />
      <Skeleton width="90%" />
      <Skeleton width="70%" />
    </div>
  );
}
