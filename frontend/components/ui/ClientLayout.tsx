"use client";

import { PageLoadingBar } from "./PageLoadingBar";
import { Navigation } from "./Navigation";

export function ClientLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <PageLoadingBar />
      <Navigation />
      {children}
    </>
  );
}

