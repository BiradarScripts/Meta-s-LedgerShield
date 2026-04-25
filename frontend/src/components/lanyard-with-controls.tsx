"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import Lanyard from "@/components/ui/lanyard";
import CardTemplate, { type CardTemplateRef, type CardVariant } from "@/components/card-template";

interface LanyardWithControlsProps {
  position?: [number, number, number];
  containerClassName?: string;
}

const ATTENDEE_NAME = "Team Ecommerce Downfall";
const HACKATHON_LABEL = "Meta Scalar Hackathon";
const CARD_VARIANT: CardVariant = "dark";

export default function LanyardWithControls({
  position = [0, 0, 20],
  containerClassName,
}: LanyardWithControlsProps) {
  const [cardTextureUrl, setCardTextureUrl] = useState<string | undefined>(undefined);
  const [textureKey, setTextureKey] = useState(0);
  const cardTemplateRef = useRef<CardTemplateRef>(null);

  const handleTextureReady = useCallback((dataUrl: string) => {
    setCardTextureUrl(dataUrl);
    setTextureKey((prev) => prev + 1);
  }, []);

  useEffect(() => {
    const timer = setTimeout(async () => {
      await cardTemplateRef.current?.captureTexture();
    }, 120);
    return () => clearTimeout(timer);
  }, []);

  return (
    <div className="flex flex-col">
      <CardTemplate
        ref={cardTemplateRef}
        userName={ATTENDEE_NAME}
        variant={CARD_VARIANT}
        onTextureReady={handleTextureReady}
        city={HACKATHON_LABEL}
        date={ATTENDEE_NAME}
      />
      <Lanyard
        key={textureKey}
        position={position}
        containerClassName={containerClassName}
        cardTextureUrl={cardTextureUrl}
      />
      <div className="border-t border-white/10 bg-black/70 px-6 py-4 backdrop-blur-sm">
        <div className="mx-auto flex w-full max-w-4xl items-center justify-center">
          <p className="font-mono text-sm uppercase tracking-[0.22em] text-zinc-300">
            Made for OpenEnv Hackathon 2026
          </p>
        </div>
      </div>
    </div>
  );
}
