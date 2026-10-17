import { api } from "./client";
import type { Experiment, Persona } from "./types";

export interface ExperimentCreateInput {
  name: string;
  productDescription: string;
  targetAudience?: string;
  researchObjectives?: string;
}

export interface ExperimentSummary extends Experiment {
  personaCount: number;
  surveyCount: number;
}

export interface UploadedDocument {
  id: string;
  filename: string;
  sizeBytes: number;
  extractedChars: number;
}

export const experimentsApi = {
  list: () => api.get<ExperimentSummary[]>("/experiments").then((r) => r.data),
  create: (body: ExperimentCreateInput) => api.post<Experiment>("/experiments", body).then((r) => r.data),
  get: (id: string) => api.get<Experiment>(`/experiments/${id}`).then((r) => r.data),
  generatePersonas: (id: string, count: number) =>
    api.post<Persona[]>(`/experiments/${id}/personas/generate`, { count }).then((r) => r.data),
  listPersonas: (id: string) => api.get<Persona[]>(`/experiments/${id}/personas`).then((r) => r.data),
  uploadDocument: (id: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return api
      .post<UploadedDocument>(`/experiments/${id}/documents`, form, { headers: { "Content-Type": "multipart/form-data" } })
      .then((r) => r.data);
  },
  listDocuments: (id: string) => api.get<UploadedDocument[]>(`/experiments/${id}/documents`).then((r) => r.data),
};
