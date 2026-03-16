import Link from "next/link";
import type { ReactNode } from "react";

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
              Projects
            </Link>
            <Link href="/app/settings" className="muted">
              Settings
            </Link>
          </div>
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
}
