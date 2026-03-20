import Link from "next/link";
import type { ReactNode } from "react";
import { Suspense } from "react";

export function NavShell({ children }: { children: ReactNode }) {
  return (
    <div className="shell">
      <a className="skip-link" href="#main-content">
        跳到主要内容
      </a>
      <header className="topbar">
        <div className="topbar-inner">
          <Link className="brand" href="/app/projects">
            PlotWeaver
          </Link>
          <nav className="step-row desktop-nav" aria-label="主导航">
            <Link href="/app/projects" className="muted">
              项目
            </Link>
            <Link href="/app/settings" className="muted">
              设置
            </Link>
          </nav>
          <details className="mobile-menu">
            <summary>菜单</summary>
            <div className="stack">
              <Link href="/app/projects" className="muted">
                项目
              </Link>
              <Link href="/app/settings" className="muted">
                设置
              </Link>
            </div>
          </details>
        </div>
      </header>
      <Suspense fallback={<main className="container"><section className="card">页面加载中...</section></main>}>
        <main id="main-content">{children}</main>
      </Suspense>
    </div>
  );
}
