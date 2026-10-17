import { api } from "./client";
import type { InterviewMessage, InterviewSummary, PostMessageResult } from "./types";

export const interviewsApi = {
  listByExperiment: (experimentId: string) =>
    api.get<InterviewSummary[]>("/interviews", { params: { experimentId } }).then((r) => r.data),
  create: (experimentId: string, personaId: string) =>
    api.post<InterviewSummary>("/interviews", { experimentId, personaId }).then((r) => r.data),
  get: (id: string) => api.get<InterviewSummary>(`/interviews/${id}`).then((r) => r.data),
  postMessage: (id: string, content: string, clientMessageId?: string) =>
    api.post<PostMessageResult>(`/interviews/${id}/messages`, { content, clientMessageId }).then((r) => r.data),
  history: (id: string) =>
    api.get<{ interviewId: string; messages: InterviewMessage[] }>(`/interviews/${id}/history`).then((r) => r.data),
};
