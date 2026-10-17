import type { Persona } from "../../api/types";
import { SegmentBadge } from "../ui/Badge";
import "./PersonaCard.css";

function initials(name: string) {
  return name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join("");
}

const PALETTE = ["#6c4df0", "#1f9d6c", "#d6455a", "#a257c9", "#2277c9", "#b57e12"];

function colorFor(seed: string) {
  let hash = 0;
  for (const ch of seed) hash = (hash * 31 + ch.charCodeAt(0)) >>> 0;
  return PALETTE[hash % PALETTE.length];
}

export function PersonaCard({
  persona,
  selected,
  onToggle,
  onClick,
}: {
  persona: Persona;
  selected?: boolean;
  onToggle?: (id: string) => void;
  onClick?: (persona: Persona) => void;
}) {
  const color = colorFor(persona.id);
  return (
    <div
      className={`persona-card${selected ? " persona-card-selected" : ""}${onClick ? " persona-card-clickable" : ""}`}
      onClick={() => onClick?.(persona)}
    >
      {onToggle && (
        <input
          type="checkbox"
          className="persona-card-check"
          checked={!!selected}
          onChange={(e) => {
            e.stopPropagation();
            onToggle(persona.id);
          }}
          onClick={(e) => e.stopPropagation()}
        />
      )}
      <div className="persona-card-top">
        <div className="persona-avatar" style={{ background: color }}>
          {initials(persona.name)}
        </div>
        <div className="persona-identity">
          <div className="persona-name">{persona.name}</div>
          <div className="persona-meta">
            {persona.age} · {persona.occupation}
          </div>
        </div>
      </div>
      <SegmentBadge segment={persona.segment} />
      <p className="persona-summary">{persona.profile?.persona_summary}</p>
      {persona.personality?.length > 0 && (
        <div className="persona-traits">
          {persona.personality.slice(0, 4).map((trait) => (
            <span key={trait} className="persona-trait">
              {trait}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
