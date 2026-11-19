// The ONLY ms <-> frame conversion helper on the Remotion side
// (AGENTS.md §4.2). Mirrors md2short/timeutil.py (round).
export const FPS = 30;

export const msToFrames = (ms: number, fps: number = FPS): number =>
  Math.round((ms * fps) / 1000);

export const framesToMs = (frames: number, fps: number = FPS): number =>
  Math.round((frames * 1000) / fps);
