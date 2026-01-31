import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FactTrace - AI Jury Verdict",
  description: "Multi-agent AI jury system for fact-checking claims",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased">{children}</body>
    </html>
  );
}
