import React from "react";
import { Sequence, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { CONTENT_HEIGHT, CONTENT_TOP, FONT_DISPLAY, HEIGHT, WIDTH } from "./layout";
import { msToFrames } from "./time";
import type { Headline } from "./types";

const HEADLINE_BOTTOM_GAP = 40;

const Card: React.FC<{ headline: Headline; durationInFrames: number }> = ({ headline, durationInFrames }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const exit = interpolate(frame, [durationInFrames - 6, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        bottom: HEIGHT - (CONTENT_TOP + CONTENT_HEIGHT) + HEADLINE_BOTTOM_GAP,
        left: 0,
        width: WIDTH,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 14,
        opacity: exit,
      }}
    >
      {headline.lines.map((line, i) => {
        // Lines pop in one after another (8 frames apart).
        const pop = spring({ frame: frame - i * 8, fps, config: { damping: 12, stiffness: 170, mass: 0.7 } });
        return (
          <div
            key={`${i}-${line}`}
            style={{
              transform: `scale(${pop}) rotate(${(i % 2 === 0 ? -2 : 2) * pop}deg)`,
              backgroundColor: i === 0 ? "#FFD600" : "#111111",
              color: i === 0 ? "#111111" : "#FFD600",
              border: "7px solid #111111",
              borderRadius: 24,
              padding: "10px 40px",
              boxShadow: "8px 10px 0 rgba(0,0,0,0.85)",
              fontFamily: FONT_DISPLAY,
              fontWeight: 900,
              fontSize: 84,
              lineHeight: 1.1,
              whiteSpace: "nowrap",
            }}
          >
            {line}
          </div>
        );
      })}
    </div>
  );
};

// Hook headline: the key "number + period" phrases of the first sentence, shown
// over the bottom of the image area while the hook is read (headline from props).
export const HeadlineLayer: React.FC<{ headline: Headline | null }> = ({ headline }) => {
  const { fps } = useVideoConfig();
  if (!headline || headline.lines.length === 0) {
    return null;
  }
  const durationInFrames = Math.max(1, msToFrames(headline.durationMs, fps));
  return (
    <Sequence from={msToFrames(headline.startMs, fps)} durationInFrames={durationInFrames} layout="none">
      <Card headline={headline} durationInFrames={durationInFrames} />
    </Sequence>
  );
};
