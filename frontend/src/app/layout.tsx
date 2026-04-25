import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Dither from "@/components/Dither";
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
        <div className="relative z-10">{children}</div>
      </body>
    </html>
  );
}