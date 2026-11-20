import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { BOTTOM_BAR_HEIGHT, FONT_CAPTION, WIDTH } from "./layout";
import { msToFrames } from "./time";
import type { CaptionSegment, Word } from "./types";

// Caption rules (architecture.md §5.4, mirrored by md2short/caption_plan.py).
export const SENTENCE_END_RE = /[.!?。！？…]$/;
export const SENTENCE_GAP_MS = 600;
export const DEFAULT_CHUNK_SIZE = 14;
export const MAX_CHUNK_SIZE = 24;

const CAPTION_HOLD_MS = 800;
// Near-fixed size: long segments wrap to a 3rd line instead of shrinking.
const MAX_FONT_SIZE = 68;
const MIN_FONT_SIZE = 56;
const TEXT_WIDTH = 1000;
const MAX_LINES = 3;
// Captions hug the top of the bottom bar (just under the image) so they stay
// above the Shorts/Reels title + channel overlay near the screen bottom.
const CAPTION_TOP_PADDING = 36;
const UNSPOKEN_OPACITY = 0.8;
const HIGHLIGHT_COLOR = "#FFD600";
const DOWN_HIGHLIGHT_COLOR = "#FF5A5A";
const DOWN_KEYWORD_RE = /하락|급락|폭락|추락|감소|약세|매도|손절|부진|적자/;

type CaptionToken = { text: string; start: number | null; end: number | null };

type CaptionChunk = {
  tokens: CaptionToken[];
  startMs: number;
  endMs: number;
};

export const clampChunkSize = (chunkSize: number): number => {
  if (!Number.isFinite(chunkSize) || chunkSize < 1) {
    return DEFAULT_CHUNK_SIZE;
  }
  return Math.min(MAX_CHUNK_SIZE, Math.floor(chunkSize));
};

// Sentence-level chunking: boundary after a word ending with .!?。！？… or when
// the gap to the next word is >= 600ms; chunkSize is the safety cap.
export const chunkBySentences = (words: Word[], chunkSize: number): Word[][] => {
  const cap = clampChunkSize(chunkSize);
  const chunks: Word[][] = [];
  let current: Word[] = [];
  words.forEach((word, i) => {
    current.push(word);
    const next = words[i + 1];
    const endsSentence = SENTENCE_END_RE.test(word.text.trim());
    const longGap = next !== undefined && next.start - word.end >= SENTENCE_GAP_MS;
    if (endsSentence || longGap || current.length >= cap || next === undefined) {
      chunks.push(current);
      current = [];
    }
  });
  return chunks;
};

const toTokens = (words: Word[]): CaptionToken[] =>
  words.map((w) => ({ text: w.text, start: w.start, end: w.end }));

const buildChunks = (
  words: Word[],
  segments: CaptionSegment[],
  chunkSize: number,
  suppressUntilMs: number,
): CaptionChunk[] => {
  const visible = (w: Word) => w.end > suppressUntilMs;

  const raw: CaptionChunk[] = [];
  if (segments.length > 0) {
    for (const seg of segments) {
      const segWords = words.slice(seg.wordStart, seg.wordEnd).filter(visible);
      if (segWords.length > 0) {
        raw.push({
          tokens: toTokens(segWords),
          startMs: Math.max(seg.startMs, segWords[0].start),
          endMs: Math.max(seg.endMs, segWords[segWords.length - 1].end),
        });
      } else if (seg.endMs > suppressUntilMs && seg.text.trim().length > 0) {
        raw.push({
          tokens: seg.text
            .trim()
            .split(/\s+/)
            .map((text) => ({ text, start: null, end: null })),
          startMs: Math.max(seg.startMs, suppressUntilMs),
          endMs: seg.endMs,
        });
      }
    }
  } else {
    for (const group of chunkBySentences(words.filter(visible), chunkSize)) {
      raw.push({
        tokens: toTokens(group),
        startMs: group[0].start,
        endMs: group[group.length - 1].end,
      });
    }
  }

  // Hold each chunk until the next one starts (bounded) so captions don't flicker.
  return raw.map((chunk, i) => {
    const next = raw[i + 1];
    const holdEnd = chunk.endMs + CAPTION_HOLD_MS;
    return {
      ...chunk,
      endMs: next ? Math.max(chunk.endMs, Math.min(next.startMs, holdEnd)) : holdEnd,
    };
  });
};

const normalize = (text: string) => text.replace(/[\s.,!?。！？…"'“”‘’()[\]{}:;~·-]/g, "");

type Highlight = { index: number; keyword: string } | null;

// One keyword per chunk: the longest keyword that appears in a token.
const pickHighlight = (tokens: CaptionToken[], keywords: string[]): Highlight => {
  const sorted = [...keywords]
    .map(normalize)
    .filter((k) => k.length > 0)
    .sort((a, b) => b.length - a.length);
  for (const keyword of sorted) {
    const idx = tokens.findIndex((t) => normalize(t.text).includes(keyword));
    if (idx >= 0) {
      return { index: idx, keyword };
    }
  }
  return null;
};

// Colors only the keyword inside the token ("상승이라는" -> "상승" + "이라는"),
// so particles/endings stay white. Decline keywords use red, others yellow.
const HighlightedText: React.FC<{ text: string; keyword: string }> = ({ text, keyword }) => {
  const color = DOWN_KEYWORD_RE.test(keyword) ? DOWN_HIGHLIGHT_COLOR : HIGHLIGHT_COLOR;
  const at = text.indexOf(keyword);
  if (at < 0) {
    return <span style={{ color }}>{text}</span>;
  }
  return (
    <>
      {text.slice(0, at)}
      <span style={{ color }}>{keyword}</span>
      {text.slice(at + keyword.length)}
    </>
  );
};

const fontSizeFor = (tokens: CaptionToken[]): number => {
  const chars = tokens.reduce((sum, t) => sum + t.text.length, 0) + Math.max(0, tokens.length - 1) * 0.35;
  const fitting = Math.floor((TEXT_WIDTH * MAX_LINES * 0.9) / Math.max(1, chars));
  return Math.max(MIN_FONT_SIZE, Math.min(MAX_FONT_SIZE, fitting));
};

export const Captions: React.FC<{
  words: Word[];
  captionSegments: CaptionSegment[];
  chunkSize: number;
  highlightKeywords: string[];
  showOpening: boolean;
  openingDurationMs: number;
}> = ({ words, captionSegments, chunkSize, highlightKeywords, showOpening, openingDurationMs }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const chunks = React.useMemo(
    () => buildChunks(words, captionSegments, chunkSize, showOpening ? openingDurationMs : 0),
    [words, captionSegments, chunkSize, showOpening, openingDurationMs],
  );

  const active = chunks.find(
    (c) => frame >= msToFrames(c.startMs, fps) && frame < msToFrames(c.endMs, fps),
  );
  if (!active) {
    return null;
  }

  const fontSize = fontSizeFor(active.tokens);
  const highlight = pickHighlight(active.tokens, highlightKeywords);
  const lineHeight = 1.3;

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        bottom: 0,
        width: WIDTH,
        height: BOTTOM_BAR_HEIGHT,
        boxSizing: "border-box",
        paddingTop: CAPTION_TOP_PADDING,
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
      }}
    >
      <div
        style={{
          width: TEXT_WIDTH,
          maxHeight: fontSize * lineHeight * MAX_LINES + 8,
          overflow: "hidden",
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          alignContent: "center",
          columnGap: fontSize * 0.3,
          fontFamily: FONT_CAPTION,
          fontWeight: 800,
          fontSize,
          lineHeight,
          wordBreak: "keep-all",
        }}
      >
        {active.tokens.map((token, i) => {
          const timed = token.start !== null && token.end !== null;
          const startF = timed ? msToFrames(token.start as number, fps) : 0;
          const endF = timed ? msToFrames(token.end as number, fps) : 0;
          const isActive = timed && frame >= startF && frame < Math.max(endF, startF + 1);
          const spoken = !timed || frame >= startF;
          const scale = isActive
            ? interpolate(frame, [startF, startF + 3, startF + 6], [1, 1.14, 1.06], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              })
            : 1;
          return (
            <span
              key={`${i}-${token.text}`}
              style={{
                display: "inline-block",
                color: "#FFFFFF",
                opacity: spoken ? 1 : UNSPOKEN_OPACITY,
                transform: `scale(${scale})`,
                textShadow: "0 4px 10px rgba(0,0,0,0.6)",
              }}
            >
              {highlight && i === highlight.index ? (
                <HighlightedText text={token.text} keyword={highlight.keyword} />
              ) : (
                token.text
              )}
            </span>
          );
        })}
      </div>
    </div>
  );
};
