import { api } from "./client";
import type { Experiment, QuestionType } from "./types";

export interface ScenarioSummary {
  slug: string;
  domain: string;
  title: string;
  description: string;
  productDescription: string;
  targetAudience: string;
  researchObjectives: string;
}

export interface SuggestedQuestion {
  question: string;
  type: QuestionType;
  options?: string[];
  scaleMin?: number;
  scaleMax?: number;
}

export interface ScenarioLaunchResult {
  experiment: Experiment;
  suggestedQuestions: SuggestedQuestion[];
}

export const scenariosApi = {
  list: () => api.get<ScenarioSummary[]>("/scenarios").then((r) => r.data),
  launch: (slug: string) => api.post<ScenarioLaunchResult>(`/scenarios/${slug}/launch`).then((r) => r.data),
};
