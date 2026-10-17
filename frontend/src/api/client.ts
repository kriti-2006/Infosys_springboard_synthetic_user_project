import axios from "axios";

export const apiBase = import.meta.env.VITE_API_BASE_URL || "/api";

export const api = axios.create({
  baseURL: apiBase,
  headers: {
    "Content-Type": "application/json",
    ...(import.meta.env.VITE_API_KEY ? { "X-API-Key": import.meta.env.VITE_API_KEY } : {}),
  },
});

export interface ApiErrorBody {
  error: { code: string; message: string; requestId: string };
}

export function errorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const body = err.response?.data as ApiErrorBody | undefined;
    if (body?.error?.message) return body.error.message;
    if (err.response?.status === 429) return "Rate limit exceeded — slow down and try again.";
    if (err.code === "ECONNABORTED") return "Request timed out.";
    if (!err.response) return "Could not reach the server. Is the backend running?";
  }
  return "Something went wrong.";
}
