import Link from "next/link";
import type { ReactNode } from "react";
import { Suspense } from "react";

export function NavShell({ children }: { children: ReactNode }) {
  return (
    <div className="shell">
      <header className="topbar">
        <div className="topbar-inner">
          <Link className="brand" href="/app/projects">
            PlotWeaver
          </Link>
          <div className="step-row">
            <Link href="/app/projects" className="muted">
              项目
            </Link>
            <Link href="/app/settings" className="muted">
              设置
            </Link>
          </div>
        </div>
      </header>
      <Suspense fallback={<main className="container"><section className="card">页面加载中...</section></main>}>
        <main>{children}</main>
      </Suspense>
    </div>
  );
}
