import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "PlotWeaver",
  description: "PlotWeaver App Router frontend"
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
