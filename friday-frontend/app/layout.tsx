import type { Metadata } from "next";
import { IBM_Plex_Mono, Merriweather, Source_Sans_3 } from "next/font/google";
import "./globals.css";

const headingFont = Merriweather({
  subsets: ["latin"],
  variable: "--font-heading",
  weight: ["400", "700"],
});

const bodyFont = Source_Sans_3({
  subsets: ["latin"],
  variable: "--font-sans",
  weight: ["400", "500", "600"],
});

const monoFont = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  weight: ["400", "500"],
});

export const metadata: Metadata = {
  title: "Project Friday",
  description: "A self-improving, tool-using AI assistant",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body
        className={`${headingFont.variable} ${bodyFont.variable} ${monoFont.variable}`}
      >
        {children}
      </body>
    </html>
  );
}
