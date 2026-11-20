import React from "react";
import { Img, Sequence, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { CONTENT_HEIGHT, CONTENT_TOP } from "./layout";
import { msToFrames } from "./time";
import type { CompanyLogoCue } from "./types";

const LOGO_SIZE = 200;

const Logo: React.FC<{ cue: CompanyLogoCue }> = ({ cue }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 13, stiffness: 160 } });
  return (
    <div
      style={{
        position: "absolute",
        top: CONTENT_TOP + CONTENT_HEIGHT - LOGO_SIZE - 90,
        right: 40,
        width: LOGO_SIZE,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        transform: `scale(${pop})`,
      }}
    >
      {/* Logo only: the logo image already carries the name, so no duplicate label. */}
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
    </div>
  );
};

// Company logo overlay for companyLogoCues (logos from public/company/<slug>.png).
export const CompanyLogos: React.FC<{ cues: CompanyLogoCue[] }> = ({ cues }) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {cues.map((cue, index) => (
        <Sequence
          key={`${index}-${cue.logoFileName}`}
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
