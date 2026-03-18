import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "PlotWeaver",
  description: "PlotWeaver App Router frontend",
  other: {
    google: "notranslate"
  }
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" translate="no" className="notranslate">
      <body translate="no" className="notranslate">
        {children}
      </body>
    </html>
  );
}
