"use client";

import { useState, useTransition } from "react";
import { useRouter } from "next/navigation";
import { useForm } from "react-hook-form";

import { clientApi } from "@/lib/api/client";
import { mapApiErrorMessage } from "@/lib/api/error-message";

type ConfigureRunFormProps = {
  projectId: string;
  chapterId: string;
  baseChapterId?: string;
  targetChapterId?: string;
};

type FormValues = {
  chapterGoal: string;
  mustInclude: string;
  mustNotInclude: string;
  continuityConstraints: string;
};

export function ConfigureRunForm({ projectId, chapterId, baseChapterId, targetChapterId }: ConfigureRunFormProps) {
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
          chapter_goal: values.chapterGoal,
          must_include: listFromLines(values.mustInclude),
          must_not_include: listFromLines(values.mustNotInclude),
          continuity_constraints: listFromLines(values.continuityConstraints),
          tone: "",
          target_length: 0,
          optional_notes: ""
        };

        const requirement = await clientApi.createRequirement(projectId, {
          chapter_goal: values.chapterGoal,
          payload_json: payloadJson,
          source: "WEB"
        });

        const run = await clientApi.createRun({
          project_id: projectId,
          base_chapter_id: baseChapterId ?? chapterId,
          target_chapter_id: targetChapterId,
          requirement_id: requirement.id,
          idempotency_key: `${projectId}-${baseChapterId ?? chapterId}-${Date.now()}`
        });

        router.push(`/app/projects/${projectId}/chapters/${targetChapterId ?? chapterId}/runs/${run.id}`);
      } catch (error) {
        setSubmitError(mapApiErrorMessage(error, "创建 requirement 或 run 失败"));
      }
    });
  };

  return (
    <form className="stack" onSubmit={handleSubmit(onSubmit)}>
      <div>
        <label htmlFor="chapterGoal">章节目标</label>
        <textarea
          id="chapterGoal"
          rows={4}
          {...register("chapterGoal", { required: "章节目标不能为空" })}
        />
        {errors.chapterGoal ? <p className="status-danger">{errors.chapterGoal.message}</p> : null}
      </div>
      <div>
        <label htmlFor="mustInclude">必须包含（每行一个）</label>
        <textarea id="mustInclude" rows={5} {...register("mustInclude")} />
      </div>
      <div>
        <label htmlFor="mustNotInclude">不得包含（每行一个）</label>
        <textarea id="mustNotInclude" rows={5} {...register("mustNotInclude")} />
      </div>
      <div>
        <label htmlFor="continuityConstraints">连续性约束（每行一个）</label>
        <textarea id="continuityConstraints" rows={5} {...register("continuityConstraints")} />
      </div>
      <div className="step-row">
        <button type="submit" disabled={pending}>
          {pending ? "创建中..." : "创建需求并进入执行"}
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
