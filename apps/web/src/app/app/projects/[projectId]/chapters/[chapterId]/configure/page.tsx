import { ConfigureRunForm } from "@/components/configure-run-form";
import { serverApi } from "@/lib/api/server";

type Props = {
  params: Promise<{ projectId: string; chapterId: string }>;
};

export default async function ConfigureContinuationPage({ params }: Props) {
  const { projectId, chapterId } = await params;
  const chapters = await serverApi.listChapters(projectId).catch(() => []);

  const sorted = [...chapters].sort((a, b) => a.order_index - b.order_index);
  const currentIdx = sorted.findIndex((item) => item.id === chapterId);
  const nextChapterId = currentIdx >= 0 && currentIdx + 1 < sorted.length ? sorted[currentIdx + 1].id : undefined;

  return (
    <div className="container">
      <section className="card stack">
        <h1>续写配置</h1>
        <p className="muted">填写 requirement 后自动创建 run 并进入执行页。若存在上一章，将自动作为续写基底。</p>
      </section>
      <section className="card">
        <ConfigureRunForm projectId={projectId} chapterId={chapterId} baseChapterId={chapterId} targetChapterId={nextChapterId} />
      </section>
    </div>
  );
}
