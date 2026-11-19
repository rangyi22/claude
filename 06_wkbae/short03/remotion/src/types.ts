// Shared Remotion types. props.json keys must match architecture.md §4.3.

export type Word = {
  text: string;
  start: number; // ms
  end: number; // ms
};

export type WordsDoc = {
  language_code?: string;
  audio_duration_ms?: number;
  text?: string;
  words: Word[];
};

export type AssetKind = "emoticon" | "photo";

export type EmoticonCue = {
  emoticonFileName: string; // path relative to remotion/public
  startMs: number;
  durationMs: number;
  keyword?: string;
  assetKind?: AssetKind;
  visualMode?: string;
  primaryVisualSubject?: string;
  visualKeywords?: string[];
};

export type CaptionSegment = {
  index: number;
  startMs: number;
  endMs: number;
  text: string;
  wordStart: number; // inclusive index into words.json words
  wordEnd: number; // exclusive
};

export type CompanyLogoCue = {
  logoFileName: string; // e.g. company/apple.png
  name: string;
  startMs: number;
  durationMs: number;
};

export type NumberCard = {
  text: string;
  startMs: number;
  durationMs: number;
};

export type CueProps = {
  audioFileName: string;
  wordsFileName: string;
  bgColor: string;
  chunkSize: number;
  emoticonCues: EmoticonCue[];
  captionSegments: CaptionSegment[];
  companyLogoCues: CompanyLogoCue[];
  numberCards: NumberCard[];
  highlightKeywords: string[];
  openingText: string;
  openingDurationMs: number;
  showOpening: boolean;
  ctaText: string;
  showOutro: boolean;
  durationInFrames: number;
};
