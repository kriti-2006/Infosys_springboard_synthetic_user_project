import type { Sentiment } from "../../api/types";
import "./SentimentBar.css";

/* Rendering order keeps red/green non-adjacent (validated via dataviz skill's
   validate_palette.js): positive -> mixed -> neutral -> negative. */
const ORDER: Sentiment[] = ["positive", "mixed", "neutral", "negative"];
const LABEL: Record<Sentiment, string> = { positive: "Positive", mixed: "Mixed", neutral: "Neutral", negative: "Negative" };

export function SentimentBar({ data, compact }: { data: Record<Sentiment, number>; compact?: boolean }) {
  return (
    <div className="sentiment-bar-root">
      <div className="sentiment-bar-track" role="img" aria-label={ORDER.map((k) => `${LABEL[k]} ${data[k] ?? 0}%`).join(", ")}>
        {ORDER.map((k) => {
          const pct = data[k] ?? 0;
          if (pct <= 0) return null;
          return (
            <div
              key={k}
              className={`sentiment-bar-segment sentiment-bar-${k}`}
              style={{ flexGrow: pct }}
              title={`${LABEL[k]}: ${pct}%`}
            >
              {!compact && pct >= 12 && <span className="sentiment-bar-label">{pct}%</span>}
            </div>
          );
        })}
      </div>
      {!compact && (
        <div className="sentiment-bar-legend">
          {ORDER.map((k) => (
            <span key={k} className="sentiment-bar-legend-item">
              <span className={`sentiment-bar-swatch sentiment-bar-${k}`} />
              {LABEL[k]} · {data[k] ?? 0}%
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
