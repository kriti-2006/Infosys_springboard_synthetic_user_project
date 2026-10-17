import "./AdoptionMeter.css";

export function AdoptionMeter({ score, size = "md" }: { score: number; size?: "sm" | "md" | "lg" }) {
  return (
    <div className={`adoption-meter adoption-meter-${size}`}>
      <div className="adoption-meter-track">
        <div className="adoption-meter-fill" style={{ width: `${Math.max(0, Math.min(100, score))}%` }} />
      </div>
      <div className="adoption-meter-value">{Math.round(score)}</div>
    </div>
  );
}
