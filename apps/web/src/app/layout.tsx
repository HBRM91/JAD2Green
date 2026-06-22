import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Adrar AI",
  description: "Regulatory sustainability reporting for bureaux d'étude",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
