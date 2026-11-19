import React from "react";
import { Img, Sequence, staticFile, useVideoConfig } from "remotion";
import { CONTENT_HEIGHT, CONTENT_TOP, WIDTH } from "./layout";
import { msToFrames } from "./time";
import type { EmoticonCue } from "./types";

// Legacy emoticon renderer: static, centered, square contain.
// The composition root uses VisualLayer.tsx instead.
export const Emoticons: React.FC<{ cues: EmoticonCue[] }> = ({ cues }) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {cues.map((cue, index) => (
        <Sequence
          key={`${index}-${cue.emoticonFileName}`}
          from={msToFrames(cue.startMs, fps)}
          durationInFrames={Math.max(1, msToFrames(cue.durationMs, fps))}
          layout="none"
        >
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
            }}
          >
            <Img
              src={staticFile(cue.emoticonFileName)}
              style={{ width: 760, height: 760, objectFit: "contain" }}
            />
          </div>
        </Sequence>
      ))}
    </>
  );
};
