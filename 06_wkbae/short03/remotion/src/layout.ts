// Fixed 9:16 layout constants (architecture.md §2.3, §5.8).
export const WIDTH = 1080;
export const HEIGHT = 1920;
export const HEADER_SAFE_MARGIN = 140;
export const HEADER_LOGO_HEIGHT = 220;
export const HEADER_HEIGHT = HEADER_SAFE_MARGIN + HEADER_LOGO_HEIGHT; // 360
export const BOTTOM_BAR_HEIGHT = 380;
export const CONTENT_TOP = HEADER_HEIGHT;
export const CONTENT_HEIGHT = HEIGHT - HEADER_HEIGHT - BOTTOM_BAR_HEIGHT; // 1180
export const FONT_CAPTION = '"SeoulAlrim", "Noto Sans KR", sans-serif';
export const FONT_DISPLAY = '"SeoulNotice", "Noto Sans KR", sans-serif';
