import type { Metadata } from "next";
import "./globals.css";
import "leaflet/dist/leaflet.css";

const description = "Geospatial supply chain risk intelligence powered by PostgreSQL/PostGIS, Spring Boot, Python, and Next.js.";
const socialImage = {
  url: "/og/chainsignal-phase2-og.png",
  width: 1731,
  height: 909,
  alt: "ChainSignal geospatial supply chain risk intelligence — conceptual branding",
};

export const metadata: Metadata = {
  metadataBase: new URL(process.env.FRONTEND_ORIGIN || "http://localhost:3000"),
  title: "ChainSignal",
  description,
  openGraph: { title: "ChainSignal", description, images: [socialImage] },
  twitter: { card: "summary_large_image", title: "ChainSignal", description, images: [socialImage] },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
