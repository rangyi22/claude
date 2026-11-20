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
  logoFileName: string; // e.g. company/apple.png; "" => no real logo, draw a text badge
  name: string;
  label?: string; // Korean name for the badge ("애플")
  ticker?: string; // "AAPL" ("" for private companies)
  startMs: number;
  durationMs: number;
};

export type NumberCard = {
  text: string;
  startMs: number;
  durationMs: number;
  tone?: "up" | "down" | "neutral"; // down => red card (same rule as captions)
};

export type IndexBoardRow = {
  name: string; // "S&P 500", "나스닥", "다우" ...
  value: string; // "0.94%", "7,230" or "" (direction only)
  tone: "up" | "down" | "neutral";
  startMs: number; // row reveal = start of that index sentence (words.json)
};

export type IndexBoard = {
  rows: IndexBoardRow[];
  startMs: number;
  durationMs: number;
};

export type Headline = {
  lines: string[]; // e.g. ["5주 연속 상승", "2024년 이후 최장"]
  startMs: number; // hook sentence segment (words.json)
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
  indexBoard: IndexBoard | null;
  headline: Headline | null;
  highlightKeywords: string[];
  openingText: string;
  sourceText: string; // "데이터 기준: 11월 13일(금)" or ""
  openingDurationMs: number;
  showOpening: boolean;
  ctaText: string;
  showOutro: boolean;
  durationInFrames: number;
};
