"use client";

import { ReactNode, useMemo } from "react";

interface HeroBackgroundProps {
  children: ReactNode;
  className?: string;
}

/* Stars in upper band — above the horizon arc */
const STARS = [
  { x: 4, y: 4, r: 0.9, o: 0.5 },
  { x: 11, y: 2, r: 0.5, o: 0.35 },
  { x: 19, y: 8, r: 1.1, o: 0.65 },
  { x: 28, y: 3, r: 0.6, o: 0.3 },
  { x: 35, y: 12, r: 0.8, o: 0.45 },
  { x: 44, y: 1, r: 1.0, o: 0.55 },
  { x: 51, y: 9, r: 0.5, o: 0.32 },
  { x: 59, y: 4, r: 1.2, o: 0.6 },
  { x: 67, y: 14, r: 0.7, o: 0.4 },
  { x: 74, y: 2, r: 0.9, o: 0.5 },
  { x: 82, y: 11, r: 0.5, o: 0.28 },
  { x: 90, y: 5, r: 1.1, o: 0.55 },
  { x: 97, y: 13, r: 0.6, o: 0.38 },
  { x: 7, y: 18, r: 0.7, o: 0.42 },
  { x: 16, y: 22, r: 1.0, o: 0.5 },
  { x: 25, y: 16, r: 0.5, o: 0.3 },
  { x: 33, y: 24, r: 0.8, o: 0.48 },
  { x: 42, y: 19, r: 1.2, o: 0.62 },
  { x: 50, y: 27, r: 0.6, o: 0.33 },
  { x: 58, y: 17, r: 0.9, o: 0.5 },
  { x: 66, y: 25, r: 0.5, o: 0.3 },
  { x: 75, y: 20, r: 1.0, o: 0.58 },
  { x: 84, y: 28, r: 0.7, o: 0.4 },
  { x: 93, y: 22, r: 0.8, o: 0.45 },
  { x: 12, y: 32, r: 0.6, o: 0.35 },
  { x: 30, y: 35, r: 1.1, o: 0.52 },
  { x: 48, y: 36, r: 0.5, o: 0.3 },
  { x: 64, y: 33, r: 0.9, o: 0.5 },
  { x: 80, y: 38, r: 0.6, o: 0.36 },
  { x: 20, y: 34, r: 0.7, o: 0.4 },
  { x: 40, y: 36, r: 1.0, o: 0.5 },
  { x: 55, y: 35, r: 0.5, o: 0.3 },
  { x: 72, y: 36, r: 0.8, o: 0.45 },
  { x: 88, y: 35, r: 0.5, o: 0.32 },
];

const NOISE_SVG = `url("data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")`;

export function HeroBackground({ children, className = "" }: HeroBackgroundProps) {
  const starsMarkup = useMemo(
    () =>
      STARS.map((star, i) => (
        <circle
          key={i}
          cx={`${star.x}%`}
          cy={`${star.y}%`}
          r={star.r}
          fill="#ffffff"
          opacity={star.o}
        />
      )),
    []
  );

  return (
    <div className={`relative overflow-hidden ${className}`}>
      {/* Base — deep near-black */}
      <div className="absolute inset-0 bg-[#050505]" />

      {/* Subtle light beams: corners → center (very low opacity) */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.35]"
        style={{
          background: `
            conic-gradient(from 210deg at 0% 0%, rgba(56, 189, 248, 0.12) 0deg, transparent 35deg),
            conic-gradient(from -30deg at 100% 0%, rgba(56, 189, 248, 0.1) 0deg, transparent 35deg)
          `,
        }}
      />
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "linear-gradient(180deg, rgba(5, 5, 5, 0.2) 0%, #050505 45%)",
        }}
      />

      {/* Blue atmospheric wash: corners + upward from horizon zone */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `
            radial-gradient(ellipse 100% 70% at 50% 42%, rgba(15, 23, 42, 0) 0%, rgba(5, 5, 5, 0.4) 55%, #050505 100%),
            radial-gradient(ellipse 90% 50% at 0% 0%, rgba(30, 58, 138, 0.25) 0%, transparent 50%),
            radial-gradient(ellipse 90% 50% at 100% 0%, rgba(30, 58, 138, 0.22) 0%, transparent 50%)
          `,
        }}
      />

      {/* Star field — top half only */}
      <svg
        className="absolute inset-0 w-full h-[40%] top-0 pointer-events-none"
        xmlns="http://www.w3.org/2000/svg"
        preserveAspectRatio="xMidYMin slice"
      >
        {starsMarkup}
      </svg>

      {/* Large radial blue glow from horizon line upward into corners */}
      <div
        className="absolute left-1/2 top-[30%] -translate-x-1/2 -translate-y-1/2 pointer-events-none w-[140%] min-w-[900px] aspect-[1.4/1]"
        style={{
          background: `radial-gradient(ellipse 50% 45% at 50% 50%,
            rgba(59, 130, 246, 0.16) 0%,
            rgba(37, 99, 235, 0.08) 35%,
            rgba(5, 5, 5, 0) 70%)`,
          filter: "blur(40px)",
        }}
      />
      <div
        className="absolute left-1/2 top-[26%] -translate-x-1/2 pointer-events-none w-[120%] min-w-[800px] h-[400px]"
        style={{
          background: `radial-gradient(ellipse 80% 100% at 50% 0%,
            rgba(34, 211, 238, 0.09) 0%,
            rgba(30, 64, 175, 0.04) 40%,
            transparent 70%)`,
          filter: "blur(28px)",
        }}
      />

      {/* Planet horizon arc — ~34% from top; stars sit above in separate layer */}
      <svg
        className="absolute inset-0 w-full h-[min(90vh,900px)] pointer-events-none"
        viewBox="0 0 1200 520"
        preserveAspectRatio="xMidYMin slice"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden
      >
        <defs>
          <linearGradient id="arc-outer" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="rgba(30, 64, 175, 0.35)" />
            <stop offset="50%" stopColor="rgba(56, 189, 248, 0.45)" />
            <stop offset="100%" stopColor="rgba(30, 64, 175, 0.35)" />
          </linearGradient>
          <linearGradient id="arc-mid" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="rgba(6, 182, 212, 0.2)" />
            <stop offset="50%" stopColor="rgba(186, 230, 253, 0.55)" />
            <stop offset="100%" stopColor="rgba(6, 182, 212, 0.2)" />
          </linearGradient>
          <filter id="hb-blur-soft" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="14" />
          </filter>
          <filter id="hb-blur-wide" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur in="SourceGraphic" stdDeviation="32" />
          </filter>
          <radialGradient id="haze-below" cx="50%" cy="0%" r="75%">
            <stop offset="0%" stopColor="rgba(15, 23, 42, 0.4)" />
            <stop offset="45%" stopColor="rgba(5, 5, 5, 0.2)" />
            <stop offset="100%" stopColor="rgba(5, 5, 5, 0)" />
          </radialGradient>
        </defs>
        <path
          d="M -100 200 Q 600 -40 1300 200"
          fill="none"
          stroke="url(#arc-outer)"
          strokeWidth="56"
          strokeLinecap="round"
          filter="url(#hb-blur-wide)"
          opacity="0.85"
        />
        <path
          d="M -40 220 Q 600 20 1240 220"
          fill="none"
          stroke="rgba(56, 189, 248, 0.35)"
          strokeWidth="28"
          strokeLinecap="round"
          filter="url(#hb-blur-soft)"
        />
        <ellipse cx="600" cy="248" rx="560" ry="180" fill="url(#haze-below)" opacity="0.95" />
        <path
          d="M 32 255 Q 600 8 1168 255"
          fill="none"
          stroke="url(#arc-mid)"
          strokeWidth="2.2"
          strokeLinecap="round"
        />
        <path
          d="M 40 256 Q 600 20 1160 256"
          fill="none"
          stroke="rgba(255, 255, 255, 0.75)"
          strokeWidth="0.65"
          strokeLinecap="round"
          opacity="0.92"
        />
      </svg>

      {/* Film grain — full-bleed */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.04] mix-blend-overlay"
        style={{ backgroundImage: NOISE_SVG }}
      />
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.02]"
        style={{ backgroundImage: NOISE_SVG, backgroundSize: "128px 128px" }}
      />

      {/* Vignette: darkens edges, keeps center readable */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: `
            radial-gradient(ellipse 75% 65% at 50% 35%, transparent 0%, rgba(5,5,5,0.4) 75%, rgba(5,5,5,0.88) 100%)
          `,
        }}
      />

      <div className="relative z-10">{children}</div>
    </div>
  );
}

export default HeroBackground;
