import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Adrar AI — Bilan Carbone",
  description: "Regulatory sustainability reporting for bureaux d'étude",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr">
      <body style={{ margin: 0, fontFamily: "system-ui, -apple-system, sans-serif" }}>
        {children}
      </body>
    </html>
  );
}
