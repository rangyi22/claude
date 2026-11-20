import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile, useVideoConfig } from "remotion";
import { BottomBar } from "./BottomBar";
import { BrandHeader } from "./BrandHeader";
import { Captions } from "./Captions";
import { CompanyLogos } from "./CompanyLogo";
import { HeadlineLayer } from "./HeadlineCard";
import { IndexBoardLayer } from "./IndexBoard";
import { NumberCards } from "./NumberCard";
import { OpeningBriefing } from "./OpeningBriefing";
import { OUTRO_DURATION_MS, OUTRO_MIN_MS, Outro } from "./Outro";
import { VisualLayer } from "./VisualLayer";
import { useFontCss, useWords } from "./loaders";
import { msToFrames } from "./time";
import type { CueProps } from "./types";

// Composition root (architecture.md §2.3). Pure function of props + words.json.
export const TechExplainer: React.FC<CueProps> = (props) => {
  useFontCss();
  const words = useWords(props.wordsFileName);
  const { fps, durationInFrames } = useVideoConfig();

  // showOpening contract (§5.10): the date is not spoken, so nothing is
  // suppressed — the badge simply overlays the hook for openingDurationMs.
  const badgeFrames = props.showOpening ? msToFrames(Math.max(0, props.openingDurationMs), fps) : 0;

  // Outro starts with the last caption segment (words.json timing) so it never
  // covers the previous sentence, clamped to [OUTRO_MIN_MS, OUTRO_DURATION_MS].
  const maxOutro = Math.min(durationInFrames, msToFrames(OUTRO_DURATION_MS, fps));
  const minOutro = Math.min(maxOutro, msToFrames(OUTRO_MIN_MS, fps));
  const lastSegment = props.captionSegments[props.captionSegments.length - 1];
  const outroFrom = lastSegment
    ? Math.min(durationInFrames - minOutro, Math.max(durationInFrames - maxOutro, msToFrames(lastSegment.startMs, fps)))
    : durationInFrames - maxOutro;

  return (
    <AbsoluteFill style={{ backgroundColor: props.bgColor }}>
      {props.audioFileName ? <Audio src={staticFile(props.audioFileName)} /> : null}
      <VisualLayer cues={props.emoticonCues} />
      <CompanyLogos cues={props.companyLogoCues} />
      <NumberCards cards={props.numberCards} />
      <IndexBoardLayer board={props.indexBoard ?? null} />
      <HeadlineLayer headline={props.headline ?? null} />
      <BrandHeader />
      <BottomBar />
      <Captions
        words={words}
        captionSegments={props.captionSegments}
        chunkSize={props.chunkSize}
        highlightKeywords={props.highlightKeywords}
      />
      {badgeFrames > 0 && props.openingText ? (
        <Sequence from={0} durationInFrames={badgeFrames} layout="none">
          <OpeningBriefing text={props.openingText} durationInFrames={badgeFrames} />
        </Sequence>
      ) : null}
      {props.showOutro && durationInFrames - outroFrom > 0 ? (
        <Sequence from={outroFrom} durationInFrames={durationInFrames - outroFrom} layout="none">
          <Outro ctaText={props.ctaText} sourceText={props.sourceText ?? ""} />
        </Sequence>
      ) : null}
    </AbsoluteFill>
  );
};
