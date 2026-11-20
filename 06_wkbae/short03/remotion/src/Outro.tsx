import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { BOTTOM_BAR_HEIGHT, FONT_DISPLAY, HEIGHT, WIDTH } from "./layout";

export const OUTRO_DURATION_MS = 2600;
export const OUTRO_MIN_MS = 1200;
const DISCLAIMER = "본 영상은 정보 제공 목적이며 투자 권유가 아닙니다.";

// Subscribe CTA + investment disclaimer over everything except the bottom
// caption band, so the last spoken sentence stays readable (only when showOutro).
export const Outro: React.FC<{ ctaText: string; sourceText: string }> = ({ ctaText, sourceText }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const fadeIn = interpolate(frame, [0, 8], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const pop = spring({ frame, fps, config: { damping: 12, stiffness: 140 } });
  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: WIDTH,
        height: HEIGHT - BOTTOM_BAR_HEIGHT,
        backgroundColor: `rgba(0,0,0,${0.85 * fadeIn})`,
        display: "flex",
        flexDirection: "column",
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
          fontSize: 42,
          color: "rgba(255,255,255,0.92)",
          textAlign: "center",
          padding: "0 80px",
          wordBreak: "keep-all",
        }}
      >
        {DISCLAIMER}
      </div>
      {sourceText ? (
        <div
          style={{
            marginTop: 16,
            opacity: fadeIn,
            fontFamily: FONT_DISPLAY,
            fontWeight: 700,
            fontSize: 40,
            color: "#FFD600",
            textAlign: "center",
          }}
        >
          {sourceText}
        </div>
      ) : null}
    </div>
  );
};
