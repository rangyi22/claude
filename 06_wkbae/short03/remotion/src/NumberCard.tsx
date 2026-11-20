import React from "react";
import { Sequence, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { CONTENT_HEIGHT, CONTENT_TOP, FONT_DISPLAY, HEIGHT, WIDTH } from "./layout";
import { msToFrames } from "./time";
import type { NumberCard as NumberCardCue } from "./types";

export const NUMBER_CARD_DURATION_MS = 1800;
const CARD_BOTTOM_GAP = 40;

const Card: React.FC<{ text: string; index: number; durationInFrames: number; down: boolean }> = ({
  text,
  index,
  durationInFrames,
  down,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 11, stiffness: 180, mass: 0.7 } });
  const tilt = index % 2 === 0 ? -6 : 5;
  const exit = interpolate(frame, [durationInFrames - 6, durationInFrames], [1, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fontSize = text.length > 8 ? 76 : 96;

  // Bottom of the image area: emoticon art carries its own text at the top
  // ("깜짝 성장", "전량 매도!"), so a top card would cover it.
  return (
    <div
      style={{
        position: "absolute",
        bottom: HEIGHT - (CONTENT_TOP + CONTENT_HEIGHT) + CARD_BOTTOM_GAP,
        left: 0,
        width: WIDTH,
        display: "flex",
        justifyContent: "center",
        opacity: exit,
      }}
    >
      <div
        style={{
          transform: `scale(${pop}) rotate(${tilt * pop}deg)`,
          backgroundColor: down ? "#FF5A5A" : "#FFD600",
          color: down ? "#FFFFFF" : "#111111",
          border: "8px solid #111111",
          borderRadius: 28,
          padding: "18px 44px",
          boxShadow: "10px 12px 0 rgba(0,0,0,0.85)",
          fontFamily: FONT_DISPLAY,
          fontWeight: 900,
          fontSize,
          lineHeight: 1.1,
          whiteSpace: "nowrap",
        }}
      >
        {text}
      </div>
    </div>
  );
};

// Number sticker cards: 1.8s pop-in + tilt (architecture.md §5.9).
export const NumberCards: React.FC<{ cards: NumberCardCue[] }> = ({ cards }) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {cards.map((card, index) => {
        const durationInFrames = Math.max(
          1,
          msToFrames(card.durationMs > 0 ? card.durationMs : NUMBER_CARD_DURATION_MS, fps),
        );
        return (
          <Sequence
            key={`${index}-${card.text}`}
            from={msToFrames(card.startMs, fps)}
            durationInFrames={durationInFrames}
            layout="none"
          >
            <Card text={card.text} index={index} durationInFrames={durationInFrames} down={card.tone === "down"} />
          </Sequence>
        );
      })}
    </>
  );
};
