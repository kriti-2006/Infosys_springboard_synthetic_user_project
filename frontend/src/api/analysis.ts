import { api } from "./client";
import type { Insight, UsageScoreRunResult, UsageScoresResponse } from "./types";

export const analysisApi = {
  createInsights: (experimentId: string, source: "survey" | "interview" | "combined" = "combined", surveyId?: string) =>
    api.post<Insight>(`/experiments/${experimentId}/insights`, { source, surveyId }).then((r) => r.data),
  listInsights: (experimentId: string) => api.get<Insight[]>(`/experiments/${experimentId}/insights`).then((r) => r.data),
  scoreUsage: (experimentId: string) =>
    api.post<UsageScoreRunResult>(`/experiments/${experimentId}/product-usage`).then((r) => r.data),
  getUsageScores: (experimentId: string) =>
    api.get<UsageScoresResponse>(`/experiments/${experimentId}/product-usage`).then((r) => r.data),
};
