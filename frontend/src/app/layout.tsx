import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Argus AML — Agentic Anti-Money Laundering & Risk Detection",
  description:
    "Autonomous financial crime investigation and risk fusion platform with dynamic execution planning and deterministic AML typologies.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#090d16] text-slate-100 antialiased selection:bg-sky-500/30 selection:text-sky-200">
        {children}
      </body>
    </html>
  );
}
