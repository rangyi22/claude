# Company logos

Logo images used by the Remotion company logo overlay (`companyLogoCues`).

## Slug convention

- File name: `company/<slug>.png`
- `<slug>` = lowercase ASCII company name, no spaces or punctuation
  (e.g. `apple`, `sandisk`, `openai`, `microsoft`).
- A cue references the file by its path relative to `remotion/public/`:
  `{"logoFileName": "company/apple.png", "name": "Apple", "startMs": 0, "durationMs": 1800}`.
- Square PNG with transparency is recommended (current placeholders: 512×512).

## Current files

The files here are **placeholders** (colored tiles with the company name):
apple, oracle, roblox, sandisk, nvidia, microsoft, google, amazon, tesla,
meta, qualcomm, openai. Replace a logo by overwriting `<slug>.png` with the
real asset; no code change is needed. Add a company by adding `<slug>.png`.
