import React from "react";
import { Img, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { CONTENT_HEIGHT, CONTENT_TOP, FONT_DISPLAY, HEIGHT } from "./layout";
import { msToFrames } from "./time";
import type { CompanyLogoCue } from "./types";

const LOGO_SIZE = 180;
const LOGO_MARGIN = 40;
// Pop in after the 6-frame emoticon crossfade so the two don't land together.
const ENTER_DELAY_FRAMES = 6;

const TickerBadge: React.FC<{ cue: CompanyLogoCue }> = ({ cue }) => (
  <div
    style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "flex-start",
      backgroundColor: "#111111",
      border: "5px solid #FFFFFF",
      borderRadius: 24,
      padding: "10px 24px",
      boxShadow: "0 8px 20px rgba(0,0,0,0.35)",
      fontFamily: FONT_DISPLAY,
      fontWeight: 900,
      whiteSpace: "nowrap",
    }}
  >
    <span style={{ fontSize: 50, color: "#FFFFFF", lineHeight: 1.15 }}>{cue.label || cue.name}</span>
    {cue.ticker ? <span style={{ fontSize: 34, color: "#FFD600", lineHeight: 1.1 }}>{cue.ticker}</span> : null}
  </div>
);

const Logo: React.FC<{ cue: CompanyLogoCue }> = ({ cue }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame: frame - ENTER_DELAY_FRAMES, fps, config: { damping: 13, stiffness: 160 } });
  return (
    <div
      style={{
        position: "absolute",
        // Bottom-left of the image area: the right edge is the Shorts/Reels
        // like/comment button column.
        bottom: HEIGHT - (CONTENT_TOP + CONTENT_HEIGHT) + LOGO_MARGIN,
        left: LOGO_MARGIN,
        transform: `scale(${pop})`,
        transformOrigin: "bottom left",
      }}
    >
      {cue.logoFileName ? (
        <Img
          src={staticFile(cue.logoFileName)}
          alt={cue.name}
          style={{
            width: LOGO_SIZE,
            height: LOGO_SIZE,
            objectFit: "contain",
            backgroundColor: "#FFFFFF",
            borderRadius: 36,
            boxShadow: "0 8px 20px rgba(0,0,0,0.35)",
          }}
        />
      ) : (
        // No real logo file in company/<slug>.png: name + ticker text badge.
        <TickerBadge cue={cue} />
      )}
    </div>
  );
};

// Company logo / ticker badge overlay for companyLogoCues.
export const CompanyLogos: React.FC<{ cues: CompanyLogoCue[] }> = ({ cues }) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {cues.map((cue, index) => (
        <Sequence
          key={`${index}-${cue.name}`}
          from={msToFrames(cue.startMs, fps)}
          durationInFrames={Math.max(1, msToFrames(cue.durationMs, fps))}
          layout="none"
        >
          <Logo cue={cue} />
        </Sequence>
      ))}
    </>
  );
};
