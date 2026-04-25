"use client";

import { useId, type SVGProps } from "react";

type LedgerShieldLogoProps = Omit<SVGProps<SVGSVGElement>, "width" | "height"> & {
  /** Pixel width/height (square). */
  size?: number;
};

export function LedgerShieldLogo({
  className,
  size = 40,
  ...svgProps
}: LedgerShieldLogoProps) {
  const uid = useId().replace(/:/g, "");
  const gid = `ls-grad-${uid}`;

  return (
    <svg
      viewBox="0 0 200 200"
      xmlns="http://www.w3.org/2000/svg"
      width={size}
      height={size}
      className={className}
      aria-hidden
      {...svgProps}
    >
      <defs>
        <linearGradient id={gid} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style={{ stopColor: "#10b981", stopOpacity: 1 }} />
          <stop offset="50%" style={{ stopColor: "#059669", stopOpacity: 1 }} />
          <stop offset="100%" style={{ stopColor: "#84cc16", stopOpacity: 1 }} />
        </linearGradient>
      </defs>
      <circle
        cx="100"
        cy="100"
        r="90"
        stroke={`url(#${gid})`}
        strokeWidth="0.5"
        fill="none"
        strokeDasharray="0.5 8"
        opacity="0.3"
      />
      <circle
        cx="100"
        cy="100"
        r="80"
        stroke={`url(#${gid})`}
        strokeWidth="1"
        fill="none"
        strokeDasharray="1 6"
        opacity="0.4"
      />
      <circle
        cx="100"
        cy="100"
        r="70"
        stroke={`url(#${gid})`}
        strokeWidth="1"
        fill="none"
        strokeDasharray="2 12"
        opacity="0.2"
      />
      <circle cx="100" cy="10" r="5" fill="#10b981" />
      <circle cx="190" cy="100" r="4" fill="#84cc16" />
      <circle cx="100" cy="190" r="6" fill="#065f46" />
      <circle cx="10" cy="100" r="3" fill="#10b981" />
      <circle cx="163" cy="37" r="2.5" fill="#10b981" opacity="0.6" />
      <circle cx="37" cy="163" r="2.5" fill="#84cc16" opacity="0.6" />
      <circle cx="100" cy="100" r="16" fill={`url(#${gid})`} />
      <circle cx="125" cy="85" r="7" fill="#10b981" opacity="0.8" />
      <circle cx="75" cy="115" r="9" fill="#065f46" opacity="0.6" />
      <circle cx="110" cy="125" r="5" fill="#84cc16" opacity="0.9" />
      <circle cx="85" cy="80" r="4" fill="#059669" opacity="0.7" />
    </svg>
  );
}
