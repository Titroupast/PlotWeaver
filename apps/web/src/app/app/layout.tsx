import type { ReactNode } from "react";

import { NavShell } from "@/components/nav-shell";

export default function AppLayout({ children }: { children: ReactNode }) {
  return <NavShell>{children}</NavShell>;
}
