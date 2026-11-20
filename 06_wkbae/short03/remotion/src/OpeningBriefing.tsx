import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { CONTENT_HEIGHT, CONTENT_TOP, FONT_DISPLAY, WIDTH } from "./layout";

// Big centered opening box ("2026년 M월 D일\n데이브리핑"), rendered inside a
// Sequence that lasts openingDurationMs (only when showOpening).
export const OpeningBriefing: React.FC<{ text: string; durationInFrames: number }> = ({
  text,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 14, stiffness: 150 } });
  const fadeOut = interpolate(frame, [durationInFrames - 6, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const lines = text.split("\n").filter((l) => l.trim().length > 0);

  return (
    <div
      style={{
        position: "absolute",
        top: CONTENT_TOP,
        left: 0,
        width: WIDTH,
        height: CONTENT_HEIGHT,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity: fadeOut,
      }}
    >
      <div
        style={{
          transform: `scale(${pop})`,
          backgroundColor: "#111111",
          border: "10px solid #FFD600",
          borderRadius: 40,
          padding: "56px 72px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 12,
          fontFamily: FONT_DISPLAY,
          fontWeight: 900,
          color: "#FFFFFF",
          textAlign: "center",
        }}
      >
        {lines.map((line, i) => (
          <div
            key={`${i}-${line}`}
            style={{ fontSize: i === lines.length - 1 ? 120 : 84, color: i === lines.length - 1 ? "#FFD600" : "#FFFFFF" }}
          >
            {line}
          </div>
        ))}
      </div>
    </div>
  );
};
