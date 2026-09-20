import type { Metadata } from "next";
import "./globals.css";
export const metadata: Metadata = {
  title: "BottleIQ — Smarter orders. Healthier shelves.",
  description:
    "Inventory intelligence and explainable purchasing recommendations for independent liquor stores.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
