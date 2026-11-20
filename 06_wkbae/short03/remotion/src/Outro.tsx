import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { FONT_DISPLAY } from "./layout";

export const OUTRO_DURATION_MS = 2600;
const DISCLAIMER = "본 영상은 정보 제공 목적이며 투자 권유가 아닙니다.";

// Full-screen subscribe CTA + investment disclaimer for the last 2.6s (only when showOutro).
export const Outro: React.FC<{ ctaText: string }> = ({ ctaText }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fadeIn = interpolate(frame, [0, 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const pop = spring({ frame, fps, config: { damping: 12, stiffness: 140 } });
  return (
    <AbsoluteFill
      style={{
        backgroundColor: `rgba(0,0,0,${0.85 * fadeIn})`,
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          transform: `scale(${pop})`,
          fontFamily: FONT_DISPLAY,
          fontWeight: 900,
          fontSize: 110,
          color: "#FFFFFF",
          textAlign: "center",
          padding: "0 60px",
          lineHeight: 1.25,
        }}
      >
        {ctaText}
      </div>
      <div
        style={{
          marginTop: 48,
          opacity: fadeIn,
          fontFamily: FONT_DISPLAY,
          fontWeight: 700,
          fontSize: 36,
          color: "rgba(255,255,255,0.8)",
          textAlign: "center",
          padding: "0 80px",
          wordBreak: "keep-all",
        }}
      >
        {DISCLAIMER}
      </div>
    </AbsoluteFill>
  );
};
