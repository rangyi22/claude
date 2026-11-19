import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useVideoConfig } from "remotion";
import { BottomBar } from "./BottomBar";
import { BrandHeader } from "./BrandHeader";
import { Captions } from "./Captions";
import { CompanyLogos } from "./CompanyLogo";
import { NumberCards } from "./NumberCard";
import { OpeningBriefing } from "./OpeningBriefing";
import { OUTRO_DURATION_MS, Outro } from "./Outro";
import { VisualLayer } from "./VisualLayer";
import { useFontCss, useWords } from "./loaders";
import { msToFrames } from "./time";
import type { CueProps } from "./types";

// Composition root (architecture.md §2.3). Pure function of props + words.json.
export const TechExplainer: React.FC<CueProps> = (props) => {
  useFontCss();
  const words = useWords(props.wordsFileName);
  const { fps, durationInFrames } = useVideoConfig();

  // showOpening contract (§5.10): opening visual + caption/visual suppression
  // for openingDurationMs. showOpening=false => suppression is 0ms.
  const openingMs = props.showOpening ? Math.max(0, props.openingDurationMs) : 0;
  const openingFrames = msToFrames(openingMs, fps);
  const visualCues = props.emoticonCues.filter((cue) => cue.startMs + cue.durationMs > openingMs);
  const outroFrames = Math.min(durationInFrames, msToFrames(OUTRO_DURATION_MS, fps));

  return (
    <AbsoluteFill style={{ backgroundColor: props.bgColor }}>
      {props.audioFileName ? <Audio src={staticFile(props.audioFileName)} /> : null}
      <VisualLayer cues={visualCues} />
      <CompanyLogos cues={props.companyLogoCues} />
      <NumberCards cards={props.numberCards} />
      <BrandHeader />
      <BottomBar />
      <Captions
        words={words}
        captionSegments={props.captionSegments}
        chunkSize={props.chunkSize}
        highlightKeywords={props.highlightKeywords}
        showOpening={props.showOpening}
        openingDurationMs={props.openingDurationMs}
      />
      {props.showOpening && openingFrames > 0 && props.openingText ? (
        <Sequence from={0} durationInFrames={openingFrames} layout="none">
          <OpeningBriefing text={props.openingText} durationInFrames={openingFrames} />
        </Sequence>
      ) : null}
      {props.showOutro && outroFrames > 0 ? (
        <Sequence from={durationInFrames - outroFrames} durationInFrames={outroFrames} layout="none">
          <Outro ctaText={props.ctaText} />
        </Sequence>
      ) : null}
    </AbsoluteFill>
  );
};
