import React from "react";
import { CalculateMetadataFunction, Composition } from "remotion";
import { TechExplainer } from "./TechExplainer";
import { FPS } from "./time";
import { HEIGHT, WIDTH } from "./layout";
import type { CueProps } from "./types";

const defaultProps: CueProps = {
  audioFileName: "",
  wordsFileName: "",
  bgColor: "#FFFFFF",
  chunkSize: 14,
  emoticonCues: [],
  captionSegments: [],
  companyLogoCues: [],
  numberCards: [],
  highlightKeywords: [],
  openingText: "",
  openingDurationMs: 0,
  showOpening: false,
  ctaText: "🐯 구독 + 알람",
  showOutro: false,
  durationInFrames: 900,
};

const calculateMetadata: CalculateMetadataFunction<CueProps> = ({ props }) => ({
  durationInFrames: Math.max(1, Math.round(props.durationInFrames)),
});

export const RemotionRoot: React.FC = () => (
  <Composition
    id="TechExplainer"
    component={TechExplainer}
    width={WIDTH}
    height={HEIGHT}
    fps={FPS}
    durationInFrames={defaultProps.durationInFrames}
    defaultProps={defaultProps}
    calculateMetadata={calculateMetadata}
  />
);
