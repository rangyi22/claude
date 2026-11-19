import { useEffect, useState } from "react";
import { cancelRender, continueRender, delayRender, staticFile } from "remotion";
import type { Word, WordsDoc } from "./types";

const FONT_CSS_ID = "md2short-font-css";

// Loads public/font/font.css (SeoulAlrim / SeoulNotice aliases) and blocks
// rendering until the font faces are ready, so no frame renders with a
// fallback font.
export const useFontCss = (): void => {
  const [handle] = useState(() => delayRender("Loading font/font.css"));

  useEffect(() => {
    const ready = () =>
      Promise.all([
        document.fonts.load('400 64px "SeoulAlrim"', "가"),
        document.fonts.load('800 64px "SeoulAlrim"', "가"),
        document.fonts.load('800 64px "SeoulNotice"', "가"),
      ])
        .then(() => continueRender(handle))
        .catch((err) => cancelRender(err));

    const existing = document.getElementById(FONT_CSS_ID);
    if (existing) {
      ready();
      return;
    }
    const link = document.createElement("link");
    link.id = FONT_CSS_ID;
    link.rel = "stylesheet";
    link.href = staticFile("font/font.css");
    link.onload = () => {
      ready();
    };
    link.onerror = () => cancelRender(new Error("Failed to load font/font.css"));
    document.head.appendChild(link);
  }, [handle]);
};

// Fetches words.json (the single source of truth for caption timing).
export const useWords = (wordsFileName: string): Word[] => {
  const [words, setWords] = useState<Word[]>([]);
  const [handle] = useState(() => delayRender(`Loading ${wordsFileName || "words"}`));

  useEffect(() => {
    if (!wordsFileName) {
      continueRender(handle);
      return;
    }
    fetch(staticFile(wordsFileName))
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Failed to fetch ${wordsFileName}: HTTP ${res.status}`);
        }
        return res.json() as Promise<WordsDoc>;
      })
      .then((doc) => {
        setWords(Array.isArray(doc.words) ? doc.words : []);
        continueRender(handle);
      })
      .catch((err) => cancelRender(err));
  }, [wordsFileName, handle]);

  return words;
};
