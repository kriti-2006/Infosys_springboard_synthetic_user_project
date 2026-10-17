import { useRef, useState, type FormEvent } from "react";
import { useOutletContext, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import type { ExperimentContext } from "./ExperimentLayout";
import { interviewsApi } from "../../api/interviews";
import { errorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Field";
import { StatusBadge } from "../../components/ui/Badge";
import { EmptyState } from "../../components/ui/EmptyState";
import { useToast } from "../../components/ui/Toast";
import "./InterviewChat.css";

export function InterviewChat() {
  const { personas } = useOutletContext<ExperimentContext>();
  const { interviewId } = useParams<{ interviewId: string }>();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  const interviewQuery = useQuery({
    queryKey: ["interview", interviewId],
    queryFn: () => interviewsApi.get(interviewId!),
    enabled: !!interviewId,
  });

  const historyQuery = useQuery({
    queryKey: ["interview-history", interviewId],
    queryFn: () => interviewsApi.history(interviewId!),
    enabled: !!interviewId,
  });

  const send = useMutation({
    mutationFn: (content: string) => interviewsApi.postMessage(interviewId!, content, crypto.randomUUID()),
    onSuccess: (result) => {
      queryClient.setQueryData(["interview-history", interviewId], (prev: typeof historyQuery.data) =>
        prev ? { ...prev, messages: [...prev.messages, result.user, result.persona] } : prev,
      );
      setDraft("");
      setTimeout(() => bottomRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    },
    onError: (err) => toast.show(errorMessage(err), "error"),
  });

  if (!interviewQuery.data) return null;
  const persona = personas.find((p) => p.id === interviewQuery.data!.personaId);

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const content = draft.trim();
    if (content) send.mutate(content);
  }

  return (
    <div className="interview-chat">
      <aside className="interview-chat-sidebar">
        {persona ? (
          <>
            <div className="interview-chat-persona-name">{persona.name}</div>
            <div className="interview-chat-persona-meta">
              {persona.age} · {persona.occupation}
            </div>
            <StatusBadge status={interviewQuery.data.status} />
            <p className="interview-chat-persona-summary">{persona.profile?.persona_summary}</p>
            <div className="interview-chat-persona-block">
              <div className="interview-chat-persona-block-title">Personality</div>
              <div className="interview-chat-traits">
                {persona.personality.map((t) => (
                  <span key={t}>{t}</span>
                ))}
              </div>
            </div>
            <div className="interview-chat-persona-block">
              <div className="interview-chat-persona-block-title">Psychological profile</div>
              <p>{persona.psychologicalProfile}</p>
            </div>
          </>
        ) : (
          <div className="interview-chat-persona-meta">Persona not found in this experiment.</div>
        )}
      </aside>

      <section className="interview-chat-main">
        <div className="interview-chat-messages">
          {historyQuery.data?.messages.length === 0 && (
            <EmptyState title="Say hello" description="Ask this persona anything — they'll answer in character, using their memory." />
          )}
          {historyQuery.data?.messages.map((m) => (
            <div key={m.id} className={m.role === "user" ? "chat-bubble chat-bubble-user" : "chat-bubble chat-bubble-persona"}>
              <div className="chat-bubble-text">{m.content}</div>
              {m.role === "persona" && m.validation && !m.validation.accepted && (
                <div className="chat-bubble-flag">flagged for consistency review</div>
              )}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
        {interviewQuery.data.status === "active" ? (
          <form className="interview-chat-input" onSubmit={onSubmit}>
            <Input
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              placeholder="Ask a follow-up question..."
              maxLength={2000}
              disabled={send.isPending}
            />
            <Button type="submit" loading={send.isPending} disabled={!draft.trim()}>
              Send
            </Button>
          </form>
        ) : (
          <div className="interview-chat-closed">This interview is closed.</div>
        )}
      </section>
    </div>
  );
}
