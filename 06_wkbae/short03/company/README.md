# Company logos

Logo images used by the Remotion company logo overlay (`companyLogoCues`).

## How it works

- `emoticon_map.plan_company_logo_cues()` fills `logoFileName` **only when a real logo exists** at
  `company/<slug>.png`. Otherwise `logoFileName` is `""` and Remotion draws a text badge with the
  Korean name and ticker (e.g. `애플` / `AAPL`) instead.
- Add or replace a logo by dropping `<slug>.png` here; no code change is needed.
  Check trademark usage rights before adding real logos.

## Slug convention

- File name: `company/<slug>.png`
- `<slug>` = lowercase ASCII company name, no spaces or punctuation
  (e.g. `apple`, `sandisk`, `openai`, `microsoft`).
- Square PNG with transparency is recommended (512×512).

## Placeholders

`_placeholder/` keeps the old colored-tile placeholders (company name on a colored square). They are
**not** used by the renderer; copy one up to `company/<slug>.png` only if you want the tile instead
of the text badge.
