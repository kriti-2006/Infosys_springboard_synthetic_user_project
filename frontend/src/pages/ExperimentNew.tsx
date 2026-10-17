import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation } from "@tanstack/react-query";
import { experimentsApi } from "../api/experiments";
import { errorMessage } from "../api/client";
import { PageHeader } from "../components/ui/PageHeader";
import { Card, CardBody } from "../components/ui/Card";
import { FieldShell, Input, Textarea } from "../components/ui/Field";
import { Button } from "../components/ui/Button";
import { useToast } from "../components/ui/Toast";

export function ExperimentNew() {
  const navigate = useNavigate();
  const toast = useToast();
  const [name, setName] = useState("");
  const [productDescription, setProductDescription] = useState("");
  const [targetAudience, setTargetAudience] = useState("");
  const [researchObjectives, setResearchObjectives] = useState("");

  const create = useMutation({
    mutationFn: () => experimentsApi.create({ name, productDescription, targetAudience, researchObjectives }),
    onSuccess: (exp) => {
      toast.show("Experiment created", "success");
      navigate(`/experiments/${exp.id}`);
    },
    onError: (err) => toast.show(errorMessage(err), "error"),
  });

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    create.mutate();
  }

  return (
    <div>
      <PageHeader title="New research experiment" subtitle="Describe the product and audience you want synthetic personas to react to." />
      <Card>
        <CardBody>
          <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: 18, maxWidth: 640 }}>
            <FieldShell label="Experiment name">
              <Input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Meal-kit app — pricing validation"
                required
                maxLength={200}
              />
            </FieldShell>
            <FieldShell label="Product description" hint="What are you testing? Be specific — this grounds every persona's answer.">
              <Textarea
                value={productDescription}
                onChange={(e) => setProductDescription(e.target.value)}
                placeholder="A subscription meal-kit service delivering pre-portioned ingredients and recipes for busy professionals..."
                required
                maxLength={5000}
                rows={4}
              />
            </FieldShell>
            <FieldShell label="Target audience" hint="Optional, but sharpens persona generation.">
              <Textarea
                value={targetAudience}
                onChange={(e) => setTargetAudience(e.target.value)}
                placeholder="Urban professionals aged 25-40 with limited time to cook"
                maxLength={3000}
                rows={2}
              />
            </FieldShell>
            <FieldShell label="Research objectives" hint="Optional. What decision will this research inform?">
              <Textarea
                value={researchObjectives}
                onChange={(e) => setResearchObjectives(e.target.value)}
                placeholder="Validate willingness to pay at three price points and identify the biggest adoption barrier"
                maxLength={3000}
                rows={2}
              />
            </FieldShell>
            <div>
              <Button type="submit" loading={create.isPending}>
                Create experiment
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
