import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { ClientLayout } from "@/components/ui/ClientLayout";

const inter = Inter({ 
  subsets: ["latin"],
  display: "swap", // Prevents render-blocking and reduces preload warnings
});

export const metadata: Metadata = {
  title: "Trading Support Dashboard",
  description: "Real-time crypto market structure analysis and trading signals",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className={inter.className}>
        <ClientLayout>{children}</ClientLayout>
      </body>
    </html>
  );
}

