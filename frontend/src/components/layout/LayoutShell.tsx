"use client";

import { usePathname } from "next/navigation";
import { Header } from "./Header";

export function LayoutShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const showHeader = pathname !== "/";

  return (
    <>
      {showHeader && <Header />}
      <main className={showHeader ? "max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8" : ""}>
        {children}
      </main>
    </>
  );
}
