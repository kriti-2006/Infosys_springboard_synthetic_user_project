export interface Experiment {
  id: string;
  name: string;
  productDescription: string;
  targetAudience: string;
  researchObjectives: string;
  createdAt: string;
}

/** Full Milestone-2 persona profile JSON, stored/returned as-is (snake_case). */
export interface PersonaProfile {
  id: string;
  name: string;
  age: number;
  occupation: string;
  background: string;
  personality_traits: string[];
  behavioral_patterns: string[];
  psychological_profile: string;
  goals: string[];
  pain_points: string[];
  tech_savviness: "low" | "medium" | "high";
  communication_style: string;
  persona_summary: string;
}

export type Segment = "students" | "working_professionals" | "parents" | "retired" | "freelancers" | "other";

export interface Persona {
  id: string;
  experimentId: string;
  key: string;
  name: string;
  age: number;
  occupation: string;
  personality: string[];
  behavioralPatterns: string[];
  psychologicalProfile: string;
  segment: Segment;
  profile: PersonaProfile;
}

export type QuestionType =
  | "open_ended"
  | "yes_no"
  | "single_choice"
  | "multiple_choice"
  | "rating"
  | "likert"
  | "numeric"
  | "short_answer";

export interface QuestionIn {
  questionId: string;
  question: string;
  type: QuestionType;
  options?: string[] | null;
  scaleMin?: number;
  scaleMax?: number;
}

export interface SurveyQuestion {
  id: string;
  questionId: string;
  question: string;
  type: QuestionType;
  options: string[] | null;
  scaleMin: number;
  scaleMax: number;
  order: number;
}

export type SurveyStatus = "draft" | "running" | "completed" | "partial" | "failed";

export interface SurveyProgress {
  expected: number;
  completed: number;
  failed: number;
}

export interface SurveyDetail {
  id: string;
  experimentId: string;
  title: string;
  researchObjective: string;
  status: SurveyStatus;
  createdAt: string;
  completedAt: string | null;
  questions: SurveyQuestion[];
  personaIds: string[];
  progress: SurveyProgress;
}

export type Sentiment = "positive" | "neutral" | "negative" | "mixed";

export interface SurveyResponseItem {
  questionId: string;
  question: string;
  type: QuestionType;
  response: string;
  value: unknown;
  sentiment: Sentiment | null;
  confidence: number | null;
  consistencyScore: number | null;
  flagged: boolean;
  createdAt: string;
}

export interface SurveyFailure {
  personaId: string;
  questionId: string;
  status: "failed";
  error: string | null;
}

export interface SurveyResults {
  survey: Pick<SurveyDetail, "id" | "title" | "status" | "progress">;
  personas: {
    personaId: string;
    name: string | null;
    segment: Segment | null;
    responses: SurveyResponseItem[];
  }[];
  failures: SurveyFailure[];
}

export interface InterviewSummary {
  id: string;
  experimentId: string;
  personaId: string;
  personaName?: string | null;
  status: "active" | "closed";
  createdAt: string;
}

export interface InterviewMessage {
  id: string;
  role: "user" | "persona";
  content: string;
  turnNumber: number;
  relevantMemory: { content: string; layer: string }[] | null;
  validation: { accepted: boolean; consistency_score?: number } | null;
  timestamp: string;
}

export interface PostMessageResult {
  turnNumber: number;
  user: InterviewMessage;
  persona: InterviewMessage;
  replayed: boolean;
}

export interface EvidenceRef {
  personaId: string;
  questionKey: string | null;
  excerpt: string;
}

export interface Theme {
  name: string;
  description: string;
  frequency: number;
  percentage: number;
  sentiment: Sentiment;
  personaIds: string[];
  evidence: EvidenceRef[];
}

export interface AgreementPattern {
  statement: string;
  count: number;
  of: number;
  summary: string;
  personaIds: string[];
}

export interface BehavioralTrend {
  trend: string;
  segments: string[];
  personaIds: string[];
}

export interface Contradiction {
  topic: string;
  positions: { stance: string; personaIds: string[] }[];
}

export interface Outlier {
  personaId: string;
  reason: string;
}

export interface InsightData {
  participants: number;
  responsesAnalysed: number;
  responsesInPrompt: number;
  themes: Theme[];
  sentiment: Record<Sentiment, number>;
  segmentSentiment: Record<string, Record<Sentiment, number>>;
  agreementPatterns: AgreementPattern[];
  behavioralTrends: BehavioralTrend[];
  contradictions: Contradiction[];
  outliers: Outlier[];
}

export interface Insight {
  id: string;
  experimentId: string;
  sourceType: "survey" | "interview" | "combined";
  createdAt: string;
  data: InsightData;
}

export type UsageDecision = "very_unlikely" | "unlikely" | "neutral" | "likely" | "very_likely";

export interface UsageFactor {
  factor: string;
  impact: "positive" | "negative";
  weight: number;
}

export interface UsageScore {
  personaId: string;
  personaName: string;
  segment: Segment;
  score: number;
  decision: UsageDecision;
  confidence: number;
  reasoning: string;
  factors: UsageFactor[] | null;
}

export interface UsageScoresResponse {
  overallLikelihood: number | null;
  bySegment: Record<string, { likelihood: number; personas: number }>;
  scores: UsageScore[];
}

export interface UsageScoreRunFailure {
  personaId: string;
  status: "failed";
  error: string;
}

export interface UsageScoreRunResult extends UsageScoresResponse {
  scored: number;
  failed: UsageScoreRunFailure[];
}

export interface ApiError {
  code: string;
  message: string;
}
