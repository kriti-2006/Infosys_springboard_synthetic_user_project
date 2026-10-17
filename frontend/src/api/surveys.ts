import { api } from "./client";
import type { QuestionIn, SurveyDetail, SurveyResults } from "./types";

export interface SurveyCreateInput {
  experimentId: string;
  title: string;
  researchObjective?: string;
  questions: QuestionIn[];
  personaIds: string[];
}

export const surveysApi = {
  listByExperiment: (experimentId: string) =>
    api.get<SurveyDetail[]>("/surveys", { params: { experimentId } }).then((r) => r.data),
  create: (body: SurveyCreateInput) => api.post<SurveyDetail>("/surveys", body).then((r) => r.data),
  get: (id: string) => api.get<SurveyDetail>(`/surveys/${id}`).then((r) => r.data),
  run: (id: string) => api.post<{ surveyId: string; status: string }>(`/surveys/${id}/run`).then((r) => r.data),
  results: (id: string) => api.get<SurveyResults>(`/surveys/${id}/results`).then((r) => r.data),
};
