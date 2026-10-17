import { useState, type FormEvent } from "react";
import { useLocation, useNavigate, useOutletContext } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import type { ExperimentContext } from "./ExperimentLayout";
import { surveysApi } from "../../api/surveys";
import { errorMessage } from "../../api/client";
import type { QuestionIn, QuestionType } from "../../api/types";
import { Card, CardBody } from "../../components/ui/Card";
import { FieldShell, Input, Select, Textarea } from "../../components/ui/Field";
import { Button } from "../../components/ui/Button";
import { PersonaCard } from "../../components/personas/PersonaCard";
import { EmptyState } from "../../components/ui/EmptyState";
import { useToast } from "../../components/ui/Toast";
import type { SuggestedQuestion } from "../../api/scenarios";
import "./SurveyNew.css";

const QUESTION_TYPES: { value: QuestionType; label: string }[] = [
  { value: "open_ended", label: "Open-ended" },
  { value: "yes_no", label: "Yes / No" },
  { value: "single_choice", label: "Single choice" },
  { value: "multiple_choice", label: "Multiple choice" },
  { value: "rating", label: "Rating scale" },
];

interface DraftQuestion {
  localId: string;
  question: string;
  type: QuestionType;
  options: string[];
  scaleMin: number;
  scaleMax: number;
}

function newQuestion(): DraftQuestion {
  return { localId: crypto.randomUUID(), question: "", type: "open_ended", options: ["", ""], scaleMin: 1, scaleMax: 5 };
}

function fromSuggested(sq: SuggestedQuestion): DraftQuestion {
  return {
    localId: crypto.randomUUID(),
    question: sq.question,
    type: sq.type,
    options: sq.options && sq.options.length > 0 ? sq.options : ["", ""],
    scaleMin: sq.scaleMin ?? 1,
    scaleMax: sq.scaleMax ?? 5,
  };
}

export function SurveyNew() {
  const { experiment, personas } = useOutletContext<ExperimentContext>();
  const navigate = useNavigate();
  const toast = useToast();
  const location = useLocation();
  const suggested = (location.state as { suggestedQuestions?: SuggestedQuestion[] } | null)?.suggestedQuestions;

  const [title, setTitle] = useState("");
  const [researchObjective, setResearchObjective] = useState("");
  const [questions, setQuestions] = useState<DraftQuestion[]>(
    suggested && suggested.length > 0 ? suggested.map(fromSuggested) : [newQuestion()],
  );
  const [selectedPersonaIds, setSelectedPersonaIds] = useState<string[]>(personas.map((p) => p.id));

  const create = useMutation({
    mutationFn: () => {
      const payload: QuestionIn[] = questions.map((q, i) => ({
        questionId: `q${i + 1}`,
        question: q.question,
        type: q.type,
        options: q.type === "single_choice" || q.type === "multiple_choice" ? q.options.filter((o) => o.trim()) : null,
        scaleMin: q.scaleMin,
        scaleMax: q.scaleMax,
      }));
      return surveysApi.create({
        experimentId: experiment.id,
        title,
        researchObjective,
        questions: payload,
        personaIds: selectedPersonaIds,
      });
    },
    onSuccess: (survey) => {
      toast.show("Survey created", "success");
      navigate(`/experiments/${experiment.id}/surveys/${survey.id}`);
    },
    onError: (err) => toast.show(errorMessage(err), "error"),
  });

  function updateQuestion(localId: string, patch: Partial<DraftQuestion>) {
    setQuestions((qs) => qs.map((q) => (q.localId === localId ? { ...q, ...patch } : q)));
  }

  function removeQuestion(localId: string) {
    setQuestions((qs) => qs.filter((q) => q.localId !== localId));
  }

  function togglePersona(id: string) {
    setSelectedPersonaIds((ids) => (ids.includes(id) ? ids.filter((x) => x !== id) : [...ids, id]));
  }

  const canSubmit =
    title.trim().length > 0 &&
    questions.length > 0 &&
    questions.every((q) => q.question.trim().length >= 3) &&
    selectedPersonaIds.length > 0;

  if (personas.length === 0) {
    return (
      <EmptyState
        title="Generate personas first"
        description="You need at least one persona before you can create a survey. Go back to the Overview tab to generate some."
      />
    );
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (canSubmit) create.mutate();
  }

  return (
    <form onSubmit={onSubmit} className="survey-new">
      <Card style={{ marginBottom: 20 }}>
        <CardBody style={{ display: "flex", flexDirection: "column", gap: 16 }}>
          <FieldShell label="Survey title">
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Pricing & onboarding feedback" required />
          </FieldShell>
          <FieldShell label="Research objective" hint="Optional — helps the insight extraction agent later.">
            <Textarea
              value={researchObjective}
              onChange={(e) => setResearchObjective(e.target.value)}
              rows={2}
              placeholder="Understand willingness to pay and the biggest onboarding friction"
            />
          </FieldShell>
        </CardBody>
      </Card>

      <h3 className="survey-new-section-title">Questions</h3>
      <div className="survey-new-questions">
        {questions.map((q, idx) => (
          <Card key={q.localId}>
            <CardBody style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <div className="survey-new-question-head">
                <span className="survey-new-question-number">Q{idx + 1}</span>
                {questions.length > 1 && (
                  <button type="button" className="survey-new-remove" onClick={() => removeQuestion(q.localId)}>
                    Remove
                  </button>
                )}
              </div>
              <FieldShell label="Question">
                <Textarea
                  value={q.question}
                  onChange={(e) => updateQuestion(q.localId, { question: e.target.value })}
                  rows={2}
                  placeholder="How likely are you to try this product in the next month?"
                  required
                />
              </FieldShell>
              <FieldShell label="Answer type">
                <Select value={q.type} onChange={(e) => updateQuestion(q.localId, { type: e.target.value as QuestionType })}>
                  {QUESTION_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>
                      {t.label}
                    </option>
                  ))}
                </Select>
              </FieldShell>

              {(q.type === "single_choice" || q.type === "multiple_choice") && (
                <FieldShell label="Options">
                  <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                    {q.options.map((opt, oi) => (
                      <div key={oi} style={{ display: "flex", gap: 8 }}>
                        <Input
                          value={opt}
                          onChange={(e) => {
                            const options = [...q.options];
                            options[oi] = e.target.value;
                            updateQuestion(q.localId, { options });
                          }}
                          placeholder={`Option ${oi + 1}`}
                        />
                        {q.options.length > 2 && (
                          <button
                            type="button"
                            className="survey-new-remove"
                            onClick={() => updateQuestion(q.localId, { options: q.options.filter((_, i) => i !== oi) })}
                          >
                            ✕
                          </button>
                        )}
                      </div>
                    ))}
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => updateQuestion(q.localId, { options: [...q.options, ""] })}
                    >
                      + Add option
                    </Button>
                  </div>
                </FieldShell>
              )}

              {q.type === "rating" && (
                <div style={{ display: "flex", gap: 12 }}>
                  <FieldShell label="Scale min">
                    <Input
                      type="number"
                      value={q.scaleMin}
                      onChange={(e) => updateQuestion(q.localId, { scaleMin: Number(e.target.value) })}
                    />
                  </FieldShell>
                  <FieldShell label="Scale max">
                    <Input
                      type="number"
                      value={q.scaleMax}
                      onChange={(e) => updateQuestion(q.localId, { scaleMax: Number(e.target.value) })}
                    />
                  </FieldShell>
                </div>
              )}
            </CardBody>
          </Card>
        ))}
      </div>
      <Button type="button" variant="secondary" onClick={() => setQuestions((qs) => [...qs, newQuestion()])} style={{ marginTop: 12 }}>
        + Add question
      </Button>

      <h3 className="survey-new-section-title" style={{ marginTop: 32 }}>
        Personas ({selectedPersonaIds.length} of {personas.length} selected)
      </h3>
      <div className="survey-new-persona-grid">
        {personas.map((p) => (
          <PersonaCard key={p.id} persona={p} selected={selectedPersonaIds.includes(p.id)} onToggle={togglePersona} />
        ))}
      </div>

      <div className="survey-new-submit">
        <Button type="submit" loading={create.isPending} disabled={!canSubmit}>
          Create survey
        </Button>
      </div>
    </form>
  );
}
