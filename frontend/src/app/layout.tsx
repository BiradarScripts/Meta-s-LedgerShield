import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Dither from "@/components/Dither";
import { LedgerShieldLogo } from "@/components/LedgerShieldLogo";
import "./globals.css";

const geist = Geist({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "LedgerShield - AP Fraud Investigation",
  description: "Interactive benchmark for AI agents evaluating enterprise payment integrity",
};

const GITHUB_REPO_URL = "https://github.com/BiradarScripts/Meta-s-LedgerShield";

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${geist.variable} ${geistMono.variable} dark`}>
      <body className="min-h-screen bg-black text-white antialiased">
        <div className="pointer-events-none fixed inset-0 z-0">
          <Dither
            waveColor={[0.32, 0.32, 0.32]}
            disableAnimation={false}
            enableMouseInteraction
            mouseRadius={0.42}
            colorNum={4}
            pixelSize={2}
            waveAmplitude={0.35}
            waveFrequency={2.8}
            waveSpeed={0.35}
          />
        </div>
        <div className="relative z-10 flex min-h-screen flex-col">
          <div className="flex-1">{children}</div>
          <footer className="border-t border-white/15 bg-black px-6 py-8">
            <div className="mx-auto flex w-full max-w-[1600px] flex-col items-center justify-between gap-4 sm:flex-row">
              <div className="flex items-center gap-2">
                <LedgerShieldLogo size={28} className="shrink-0 opacity-90" />
                <p className="font-mono text-xs text-zinc-500">
                  LedgerShield · Meta Scalar Hackathon
                </p>
              </div>
              <a
                href={GITHUB_REPO_URL}
                target="_blank"
                rel="noopener noreferrer"
                aria-label="LedgerShield repository on GitHub"
                className="inline-flex items-center gap-2 rounded-md border border-white/20 px-3 py-2 font-mono text-xs uppercase tracking-[0.16em] text-zinc-300 transition hover:border-white/35 hover:text-white"
              >
                <svg
                  className="h-5 w-5 text-white"
                  viewBox="0 0 98 96"
                  xmlns="http://www.w3.org/2000/svg"
                  aria-hidden
                >
                  <path
                    fill="currentColor"
                    fillRule="evenodd"
                    clipRule="evenodd"
                    d="M48.854 0C21.839 0 0 22 0 49.217c0 21.756 13.993 40.172 33.405 46.69 2.427.49 3.316-1.059 3.316-2.362 0-1.141-.08-5.052-.08-9.127-13.089 2.934-16.042-5.867-16.042-5.867-2.184-5.704-5.42-7.17-5.42-7.17-4.448-3.015.324-3.015.324-3.015 4.934.326 7.523 5.052 7.523 5.052 4.367 7.496 11.404 5.378 14.235 4.074.404-3.178 1.699-5.378 3.094-6.6-10.839-1.235-22.23-5.42-22.23-24.204 0-5.378 1.94-9.778 5.014-13.2-.485-1.222-2.184-6.275.486-13.038 0 0 4.125-1.304 13.426 5.052a46.97 46.97 0 0 1 12.214-1.63c4.125 0 8.33.571 12.213 1.63 9.302-6.356 13.427-5.052 13.427-5.052 2.67 6.763.97 11.816.485 13.038 3.155 3.422 5.015 7.822 5.015 13.2 0 18.905-11.404 23.06-22.324 24.283 1.78 1.548 3.316 4.481 3.316 9.126 0 6.6-.08 11.897-.08 13.526 0 1.304.89 2.853 3.316 2.364 19.412-6.52 33.405-24.935 33.405-46.691C97.707 22 75.788 0 48.854 0z"
                  />
                </svg>
                GitHub
              </a>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}