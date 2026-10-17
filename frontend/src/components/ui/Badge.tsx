import type { ReactNode } from "react";
import clsx from "clsx";
import "./Badge.css";

type Tone = "violet" | "positive" | "negative" | "neutral" | "mixed" | "navy" | "warning";

export function Badge({ tone = "navy", children }: { tone?: Tone; children: ReactNode }) {
  return <span className={clsx("badge", `badge-${tone}`)}>{children}</span>;
}

const SENTIMENT_TONE: Record<string, Tone> = {
  positive: "positive",
  negative: "negative",
  neutral: "neutral",
  mixed: "mixed",
};

export function SentimentBadge({ sentiment }: { sentiment: string | null | undefined }) {
  if (!sentiment) return null;
  return <Badge tone={SENTIMENT_TONE[sentiment] ?? "navy"}>{sentiment}</Badge>;
}

const SEGMENT_LABEL: Record<string, string> = {
  students: "Students",
  working_professionals: "Working professionals",
  parents: "Parents",
  retired: "Retired",
  freelancers: "Freelancers",
  other: "Other",
};

export function SegmentBadge({ segment }: { segment: string | null | undefined }) {
  if (!segment) return null;
  return <Badge tone="violet">{SEGMENT_LABEL[segment] ?? segment}</Badge>;
}

const STATUS_TONE: Record<string, Tone> = {
  draft: "neutral",
  running: "warning",
  completed: "positive",
  partial: "warning",
  failed: "negative",
  active: "positive",
  closed: "neutral",
};

export function StatusBadge({ status }: { status: string }) {
  return <Badge tone={STATUS_TONE[status] ?? "navy"}>{status}</Badge>;
}
