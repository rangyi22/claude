import React from "react";
import { Sequence, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { CONTENT_HEIGHT, CONTENT_TOP, FONT_DISPLAY, HEIGHT, WIDTH } from "./layout";
import { msToFrames } from "./time";
import type { IndexBoard as IndexBoardCue, IndexBoardRow } from "./types";

const BOARD_WIDTH = 780;
const BOARD_BOTTOM_GAP = 30;
const UP_COLOR = "#E0A800";
const DOWN_COLOR = "#E53935";

const rowLabel = (row: IndexBoardRow): { text: string; color: string } => {
  if (row.tone === "down") {
    return { text: `▼ ${row.value || "하락"}`, color: DOWN_COLOR };
  }
  if (row.tone === "up") {
    return { text: `▲ ${row.value || "상승"}`, color: UP_COLOR };
  }
  return { text: row.value, color: "#111111" };
};

const Board: React.FC<{ board: IndexBoardCue; durationInFrames: number }> = ({ board, durationInFrames }) => {
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
        bottom: HEIGHT - (CONTENT_TOP + CONTENT_HEIGHT) + BOARD_BOTTOM_GAP,
        left: (WIDTH - BOARD_WIDTH) / 2,
        width: BOARD_WIDTH,
        boxSizing: "border-box",
        padding: "20px 40px",
        backgroundColor: "rgba(255,255,255,0.96)",
        border: "6px solid #111111",
        borderRadius: 28,
        boxShadow: "10px 12px 0 rgba(0,0,0,0.85)",
        fontFamily: FONT_DISPLAY,
        fontWeight: 900,
        opacity: exit,
      }}
    >
      {board.rows.map((row) => {
        // Each row pops in when its sentence starts (row.startMs from words.json segments).
        const rowFrom = msToFrames(row.startMs - board.startMs, fps);
        const pop = spring({ frame: frame - rowFrom, fps, config: { damping: 13, stiffness: 170 } });
        if (frame < rowFrom) {
          return null; // not spoken yet: the panel grows row by row
        }
        const label = rowLabel(row);
        return (
          <div
            key={row.name}
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              fontSize: 60,
              lineHeight: 1.35,
              transform: `translateX(${(1 - pop) * 60}px)`,
            }}
          >
            <span style={{ color: "#111111" }}>{row.name}</span>
            <span style={{ color: label.color }}>{label.text}</span>
          </div>
        );
      })}
    </div>
  );
};

// Index comparison board (S&P 500 / 나스닥 / 다우 ...) over the bottom of the image area.
export const IndexBoardLayer: React.FC<{ board: IndexBoardCue | null }> = ({ board }) => {
  const { fps } = useVideoConfig();
  if (!board || board.rows.length === 0) {
    return null;
  }
  const durationInFrames = Math.max(1, msToFrames(board.durationMs, fps));
  return (
    <Sequence from={msToFrames(board.startMs, fps)} durationInFrames={durationInFrames} layout="none">
      <Board board={board} durationInFrames={durationInFrames} />
    </Sequence>
  );
};
