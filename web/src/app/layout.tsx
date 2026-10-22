import type { CSSProperties, ReactNode } from "react";
import type { Metadata } from "next";
import { DM_Sans, Fraunces, Source_Serif_4 } from "next/font/google";
import Link from "next/link";
import { AuthControls } from "@/components/AuthControls";
import "./globals.css";

const fraunces = Fraunces({
  subsets: ["latin"],
  variable: "--font-fraunces",
  display: "swap",
});

const sourceSerif = Source_Serif_4({
  subsets: ["latin"],
  variable: "--font-source-serif",
  display: "swap",
});

const dmSans = DM_Sans({
  subsets: ["latin"],
  variable: "--font-dm-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "GeoMeta — learnable geographic reasoning",
  description:
    "A geographic reasoning coach for GeoGuessr players: practice cues, inspect predictions, and build a study library.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: ReactNode;
}>) {
  return (
    // After Clerk init: wrap children (or <body> content) with <ClerkProvider>.
    // import { ClerkProvider } from "@clerk/nextjs";
    <html
      lang="en"
      className={`${fraunces.variable} ${sourceSerif.variable} ${dmSans.variable}`}
    >
      <body
        style={
          {
            "--font-display": "var(--font-fraunces), Georgia, serif",
            "--font-body": "var(--font-source-serif), Georgia, serif",
            "--font-ui": "var(--font-dm-sans), sans-serif",
          } as CSSProperties
        }
      >
        {/* <ClerkProvider> */}
        <div className="site-shell">
          <header className="top-nav">
            <Link href="/" className="brand">
              Geo<span>Meta</span>
            </Link>
            <nav aria-label="Primary">
              <ul className="nav-links">
                <li>
                  <Link href="/practice">Practice</Link>
                </li>
                <li>
                  <Link href="/study">Study</Link>
                </li>
              </ul>
            </nav>
            <AuthControls />
          </header>
          <main className="main">{children}</main>
        </div>
        {/* </ClerkProvider> */}
      </body>
    </html>
  );
}
