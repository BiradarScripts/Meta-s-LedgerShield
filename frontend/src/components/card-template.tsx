"use client";

import { forwardRef, useCallback, useEffect, useImperativeHandle, useState } from "react";

export type CardVariant = "dark" | "light";

interface CardTemplateProps {
  userName: string;
  variant: CardVariant;
  onTextureReady: (dataUrl: string) => void;
  /** Lower stack: event / hackathon line (above date). */
  city?: string;
  /** Lower stack: bottom line (e.g. team name). */
  date?: string;
  /** Large label above ATTENDEE (default: BUILDER). */
  roleLabel?: string;
}

export interface CardTemplateRef {
  captureTexture: () => Promise<void>;
}

const CANVAS_SIZE = 1376;

/**
 * card.glb TEXCOORD_0: u ≈ 0–1, v ≈ 0.002–0.757 — keep type below v_max or it won’t map.
 * Stack is bottom-left so the 3D clip is less likely to cover it than bottom-right.
 */
const CARD_TEXCOORD_V_MAX = 0.757;
const STACK_TEXT_BOTTOM = Math.floor(CANVAS_SIZE * CARD_TEXCOORD_V_MAX) - 32;
const STACK_TEXT_X = 92;
const STACK_WIPE_PAD = 36;

function paintCard(
  ctx: CanvasRenderingContext2D,
  baseImage: HTMLImageElement | null,
  variant: CardVariant,
  displayName: string,
  city: string | undefined,
  date: string | undefined,
  roleLabel: string,
): void {
  const textColor = variant === "dark" ? "#ffffff" : "#000000";
  const wipe = variant === "dark" ? "#000000" : "#ffffff";
  const roleColor = variant === "dark" ? "#ffffff" : "#000000";

  if (baseImage) {
    ctx.drawImage(baseImage, 0, 0, CANVAS_SIZE, CANVAS_SIZE);
  } else {
    ctx.fillStyle = wipe;
    ctx.fillRect(0, 0, CANVAS_SIZE, CANVAS_SIZE);
  }

  ctx.fillStyle = wipe;
  ctx.fillRect(24, 34, 860, 280);
  ctx.fillRect(160, 250, 760, 180);
  ctx.fillRect(360, 780, 420, 170);
  ctx.fillRect(760, 700, 540, 240);

  const yDateLine = STACK_TEXT_BOTTOM;
  const yCityLine = STACK_TEXT_BOTTOM - 62;
  const yAttendeeLine = STACK_TEXT_BOTTOM - 124;
  const yRoleLine = STACK_TEXT_BOTTOM - 228;
  const wipeTop = Math.max(600, yRoleLine - 52);
  const wipeW = 640;
  ctx.fillRect(
    32,
    wipeTop,
    wipeW,
    STACK_TEXT_BOTTOM - wipeTop + STACK_WIPE_PAD,
  );

  ctx.fillStyle = textColor;
  ctx.font = '600 44px "Geist Mono", ui-monospace, monospace';
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  const textX = 92;
  const textY = 184;
  ctx.fillText("META SCALAR HACKATHON", textX, textY);
  ctx.fillStyle = "#b5b5b5";
  ctx.font = '600 42px "Geist Mono", ui-monospace, monospace';
  ctx.fillText(displayName.toUpperCase().slice(0, 23), textX, textY + 64);

  const role = (roleLabel || "BUILDER").toUpperCase().slice(0, 18);
  ctx.fillStyle = roleColor;
  ctx.font = '700 56px "Geist Mono", ui-monospace, monospace';
  ctx.textAlign = "left";
  ctx.textBaseline = "middle";
  ctx.fillText(role, STACK_TEXT_X, yRoleLine);

  ctx.fillStyle = "#c8c8c8";
  if (variant === "light") ctx.fillStyle = "#404040";
  ctx.font = '700 42px "Geist Mono", ui-monospace, monospace';
  ctx.fillText("ATTENDEE", STACK_TEXT_X, yAttendeeLine);

  if (city) {
    ctx.fillStyle = textColor;
    ctx.font = '600 40px "Geist Mono", ui-monospace, monospace';
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    const cityT = city.toUpperCase();
    ctx.fillText(cityT.length > 28 ? `${cityT.slice(0, 27)}…` : cityT, STACK_TEXT_X, yCityLine);
  }

  if (date) {
    ctx.fillStyle = variant === "dark" ? "#d9d9d9" : "#525252";
    ctx.font = '600 40px "Geist Mono", ui-monospace, monospace';
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    const dateT = date.toUpperCase();
    ctx.fillText(dateT.length > 28 ? `${dateT.slice(0, 27)}…` : dateT, STACK_TEXT_X, yDateLine);
  }
}

const CardTemplate = forwardRef<CardTemplateRef, CardTemplateProps>(
  ({ userName, variant, onTextureReady, city, date, roleLabel = "BUILDER" }, ref) => {
    const [baseImage, setBaseImage] = useState<HTMLImageElement | null>(null);

    const imageSrc = variant === "dark" ? "/card-base-dark.png" : "/card-base-light.png";

    useEffect(() => {
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.onload = () => setBaseImage(img);
      img.src = imageSrc;
    }, [imageSrc]);

    const captureTexture = useCallback(async () => {
      if (typeof document !== "undefined" && document.fonts?.ready) {
        await document.fonts.ready;
      }

      const canvas = document.createElement("canvas");
      canvas.width = CANVAS_SIZE;
      canvas.height = CANVAS_SIZE;
      const ctx = canvas.getContext("2d");
      if (!ctx) return;

      const displayName = userName || "TEAM ECOMMERCE DOWNFALL";
      paintCard(ctx, baseImage, variant, displayName, city, date, roleLabel);

      onTextureReady(canvas.toDataURL("image/png"));
    }, [baseImage, userName, variant, city, date, roleLabel, onTextureReady]);

    useImperativeHandle(ref, () => ({ captureTexture }), [captureTexture]);

    useEffect(() => {
      if (!baseImage) return;
      void captureTexture();
    }, [baseImage, captureTexture]);

    return null;
  },
);

CardTemplate.displayName = "CardTemplate";

export default CardTemplate;
