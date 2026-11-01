import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Failure Investigator",
  description: "Evidence-first business failure research",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
