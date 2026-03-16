"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { clientApi } from "@/lib/api/client";
import { mapApiErrorMessage } from "@/lib/api/error-message";

type ConfigureRunFormProps = {
  projectId: string;
  chapterId: string;
};

type FormValues = {
  chapterGoal: string;
  mustInclude: string;
  mustNotInclude: string;
  continuityConstraints: string;
};

export function ConfigureRunForm({ projectId, chapterId }: ConfigureRunFormProps) {
  const router = useRouter();
  const [pending, startTransition] = useTransition();
  const [submitError, setSubmitError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors }
  } = useForm<FormValues>({
    defaultValues: {
      chapterGoal: "",
      mustInclude: "",
      mustNotInclude: "",
      continuityConstraints: ""
    }
  });

  const onSubmit = (values: FormValues) => {
    startTransition(async () => {
      setSubmitError(null);
      try {
        const payloadJson = {
          must_include: listFromLines(values.mustInclude),
          must_not_include: listFromLines(values.mustNotInclude),
          continuity_constraints: listFromLines(values.continuityConstraints)
        };

        const requirement = await clientApi.createRequirement(projectId, {
          chapter_goal: values.chapterGoal,
          payload_json: payloadJson,
          source: "WEB"
        });

        const run = await clientApi.createRun({
          project_id: projectId,
          target_chapter_id: chapterId,
          requirement_id: requirement.id,
          idempotency_key: `${projectId}-${chapterId}-${Date.now()}`
        });

        router.push(`/app/projects/${projectId}/chapters/${chapterId}/runs/${run.id}`);
      } catch (error) {
        setSubmitError(mapApiErrorMessage(error, "Failed to create requirement or run"));
      }
    });
  };

  return (
    <form className="stack" onSubmit={handleSubmit(onSubmit)}>
      <div>
        <label htmlFor="chapterGoal">Chapter Goal</label>
        <textarea
          id="chapterGoal"
          rows={4}
          {...register("chapterGoal", { required: "Chapter goal is required" })}
        />
        {errors.chapterGoal ? <p className="status-danger">{errors.chapterGoal.message}</p> : null}
      </div>
      <div>
        <label htmlFor="mustInclude">Must Include (one per line)</label>
        <textarea id="mustInclude" rows={5} {...register("mustInclude")} />
      </div>
      <div>
        <label htmlFor="mustNotInclude">Must Not Include (one per line)</label>
        <textarea id="mustNotInclude" rows={5} {...register("mustNotInclude")} />
      </div>
      <div>
        <label htmlFor="continuityConstraints">Continuity Constraints (one per line)</label>
        <textarea id="continuityConstraints" rows={5} {...register("continuityConstraints")} />
      </div>
      <div className="step-row">
        <button type="submit" disabled={pending}>
          {pending ? "Creating Run..." : "Create Requirement & Run"}
        </button>
      </div>
      {submitError ? <p className="status-danger">{submitError}</p> : null}
    </form>
  );
}

function listFromLines(text: string): string[] {
  return text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}
