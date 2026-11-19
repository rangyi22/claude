import React from "react";
import { Img, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { CONTENT_HEIGHT, CONTENT_TOP, WIDTH } from "./layout";
import { msToFrames } from "./time";
import type { EmoticonCue } from "./types";

const EMOTICON_SIZE = 820;
const KEN_BURNS_ZOOM = 0.08;
const FADE_FRAMES = 6;

const isPhoto = (cue: EmoticonCue): boolean =>
  cue.assetKind === "photo" || (cue.assetKind === undefined && cue.visualMode === "photo");

const CueVisual: React.FC<{ cue: EmoticonCue; index: number; durationInFrames: number }> = ({
  cue,
  index,
  durationInFrames,
}) => {
  const frame = useCurrentFrame();
  // Gentle Ken Burns: even cues zoom in, odd cues zoom out.
  const progress = interpolate(frame, [0, Math.max(1, durationInFrames - 1)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const scale = index % 2 === 0 ? 1 + KEN_BURNS_ZOOM * progress : 1 + KEN_BURNS_ZOOM * (1 - progress);
  const opacity = interpolate(frame, [0, FADE_FRAMES], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const src = staticFile(cue.emoticonFileName);
  const photo = isPhoto(cue);

  return (
    <div
      style={{
        position: "absolute",
        top: CONTENT_TOP,
        left: 0,
        width: WIDTH,
        height: CONTENT_HEIGHT,
        overflow: "hidden",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        opacity,
      }}
    >
      {photo ? (
        <Img
          src={src}
          style={{
            width: WIDTH,
            height: CONTENT_HEIGHT,
            objectFit: "cover",
            transform: `scale(${scale})`,
          }}
        />
      ) : (
        <Img
          src={src}
          style={{
            width: EMOTICON_SIZE,
            height: EMOTICON_SIZE,
            objectFit: "contain",
            transform: `scale(${scale})`,
          }}
        />
      )}
    </div>
  );
};

// One <Sequence> per visual cue inside the safe content rect
// (between the 470px header and the 460px bottom bar).
export const VisualLayer: React.FC<{ cues: EmoticonCue[] }> = ({ cues }) => {
  const { fps } = useVideoConfig();
  return (
    <>
      {cues.map((cue, index) => {
        const from = msToFrames(cue.startMs, fps);
        const durationInFrames = Math.max(1, msToFrames(cue.durationMs, fps));
        return (
          <Sequence
            key={`${index}-${cue.emoticonFileName}`}
            from={from}
            durationInFrames={durationInFrames}
            layout="none"
          >
            <CueVisual cue={cue} index={index} durationInFrames={durationInFrames} />
          </Sequence>
        );
      })}
    </>
  );
};
