import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Adrar AI — Bilan Carbone | JAD2 Advisory",
  description: "Plateforme de reporting carbone réglementaire pour bureaux d'étude — JAD2 Advisory",
  keywords: "bilan carbone, GHG, reporting carbone, bureau d'étude, JAD2 Advisory, Maroc",
  icons: {
    icon: "/favicon.svg",
  },
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
