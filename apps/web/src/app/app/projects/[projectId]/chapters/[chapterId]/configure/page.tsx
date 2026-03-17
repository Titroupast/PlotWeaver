import { ConfigureRunForm } from "@/components/configure-run-form";

type Props = {
  params: Promise<{ projectId: string; chapterId: string }>;
};

export default async function ConfigureContinuationPage({ params }: Props) {
  const { projectId, chapterId } = await params;

  return (
    <div className="container">
      <section className="card stack">
        <h1>续写配置</h1>
        <p className="muted">填写 requirement 后将自动创建 run，并进入生成过程页面。</p>
      </section>
      <section className="card">
        <ConfigureRunForm projectId={projectId} chapterId={chapterId} />
      </section>
    </div>
  );
}