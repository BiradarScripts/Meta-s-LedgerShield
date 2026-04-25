"use client";

import { forwardRef, useImperativeHandle, useEffect, useState } from "react";

export type CardVariant = "dark" | "light";

interface CardTemplateProps {
  userName: string;
  variant: CardVariant;
  onTextureReady: (dataUrl: string) => void;
  city?: string;
  date?: string;
}

export interface CardTemplateRef {
  captureTexture: () => Promise<void>;
}

const CANVAS_SIZE = 1376;

const CardTemplate = forwardRef<CardTemplateRef, CardTemplateProps>(
  ({ userName, variant, onTextureReady, city, date }, ref) => {
    const [baseImage, setBaseImage] = useState<HTMLImageElement | null>(null);

    const imageSrc = variant === "dark" ? "/card-base-dark.png" : "/card-base-light.png";
    const textColor = variant === "dark" ? "#ffffff" : "#000000";

    useEffect(() => {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => setBaseImage(img);
      img.src = imageSrc;
    }, [imageSrc]);

    const captureTexture = async () => {
      const canvas = document.createElement("canvas");
      canvas.width = CANVAS_SIZE;
      canvas.height = CANVAS_SIZE;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      if (baseImage) {
        ctx.drawImage(baseImage, 0, 0, CANVAS_SIZE, CANVAS_SIZE);
      } else {
        ctx.fillStyle = "#000000";
        ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
      }

      // Remove reference-project branding and unrelated printed labels.
      ctx.fillStyle = variant === "dark" ? "#000000" : "#ffffff";
      // Top branding/title region (remove all remnants like "Prompt to Production")
      ctx.fillRect(24, 34, 860, 280);
      // Center title strip safety wipe
      ctx.fillRect(160, 250, 760, 180);
      // Bottom attendee old label region
      ctx.fillRect(360, 780, 420, 170);
      // Bottom-right old qr caption region
      ctx.fillRect(760, 700, 540, 240);

      const displayName = userName || "TEAM ECOMMERCE DOWNFALL";
      ctx.fillStyle = textColor;
      ctx.font = '600 44px "Geist Mono", monospace';
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      const textX = 92;
      const textY = 184;
      ctx.fillText("META SCALAR HACKATHON", textX, textY);
      ctx.fillStyle = "#b5b5b5";
      ctx.font = '600 42px "Geist Mono", monospace';
      ctx.fillText(displayName.toUpperCase().slice(0, 23), textX, textY + 64);

      // Bottom-right role label
      ctx.fillStyle = "#ffffff";
      ctx.font = '700 56px "Geist Mono", monospace';
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText("BUILDER", CANVAS_SIZE - 130, CANVAS_SIZE - 340);

      if (city) {
        ctx.fillStyle = textColor;
        ctx.font = '600 44px "Geist Mono", monospace';
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";
        const cityTextX = CANVAS_SIZE - 110;
        const cityTextY = CANVAS_SIZE - 118;
        ctx.fillText(city.toUpperCase(), cityTextX, cityTextY);
      }

      if (date) {
        ctx.fillStyle = "#d9d9d9";
        ctx.font = '600 42px "Geist Mono", monospace';
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";
        const dateTextX = CANVAS_SIZE - 110;
        const dateTextY = CANVAS_SIZE - 58;
        ctx.fillText(date.toUpperCase(), dateTextX, dateTextY);
      }

      // Keep attendee label visible.
      ctx.fillStyle = "#c8c8c8";
      ctx.font = '700 42px "Geist Mono", monospace';
      ctx.textAlign = "right";
      ctx.textBaseline = "middle";
      ctx.fillText("ATTENDEE", CANVAS_SIZE - 100, CANVAS_SIZE - 205);

      onTextureReady(canvas.toDataURL("image/png"));
    };

    useImperativeHandle(ref, () => ({ captureTexture }));
    return null;
  },
);

CardTemplate.displayName = "CardTemplate";

export default CardTemplate;
