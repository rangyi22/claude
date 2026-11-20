import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { CONTENT_TOP, FONT_DISPLAY, WIDTH } from "./layout";

// Small date badge ("2026년 M월 D일 데이브리핑") at the top of the image area,
// shown over the hook for openingDurationMs (only when showOpening). The date is
// not spoken, so the hook starts at 0s.
export const OpeningBriefing: React.FC<{ text: string; durationInFrames: number }> = ({
  text,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const drop = spring({ frame, fps, config: { damping: 14, stiffness: 160 } });
  const fadeOut = interpolate(frame, [durationInFrames - 8, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const flat = text.replace(/\s*\n\s*/g, " ").trim();
  const cut = flat.lastIndexOf(" ");
  const date = cut > 0 ? flat.slice(0, cut) : flat;
  const label = cut > 0 ? flat.slice(cut + 1) : "";

  return (
    <div
      style={{
        position: "absolute",
        top: CONTENT_TOP + 24,
        left: 0,
        width: WIDTH,
        display: "flex",
        justifyContent: "center",
        opacity: fadeOut,
        transform: `translateY(${(drop - 1) * 40}px)`,
      }}
    >
      <div
        style={{
          backgroundColor: "#111111",
          border: "5px solid #FFD600",
          borderRadius: 999,
          padding: "12px 36px",
          fontFamily: FONT_DISPLAY,
          fontWeight: 900,
          fontSize: 46,
          color: "#FFFFFF",
          whiteSpace: "nowrap",
          boxShadow: "0 8px 20px rgba(0,0,0,0.35)",
        }}
      >
        {date}
        {label ? <span style={{ color: "#FFD600", marginLeft: 14 }}>{label}</span> : null}
      </div>
    </div>
  );
};
