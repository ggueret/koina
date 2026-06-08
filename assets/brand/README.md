# koina brand assets

Monochrome wordmark with a Greek **κ** initial (a nod to *koiné*), set in **GFS
Neohellenic** and outlined to paths (no font dependency). The wordmark uses the
**Regular** weight (κ at 1.12× the body); the icons (mark, avatar, favicon) use
the **Bold** weight so the κ stays solid at small sizes. A **blue** (`#2f6f8f`)
brand color sits on the canvas (avatar, social), not on the logo itself.

## Palette

| Role  | Hex       |
| ----- | --------- |
| ink   | `#2a2320` |
| paper | `#fdf6ee` |
| blue  | `#2f6f8f` |

## Typeface

[GFS Neohellenic](https://fonts.google.com/specimen/GFS+Neohellenic) (Regular and
Bold) by the Greek Font Society, [SIL Open Font License](https://openfontlicense.org/).
The wordmark and mark are outlined, so the font is not redistributed here.

## Files

| File | Use |
| ---- | --- |
| `wordmark.svg` | primary logo (ink on cream), Regular |
| `wordmark-dark.svg` | wordmark for dark backgrounds (cream); pair via `<picture>` |
| `mark.svg` | the κ alone (ink, Bold), for tight icon contexts |
| `mark-dark.svg` | the κ alone (cream, Bold), for dark backgrounds |
| `avatar.svg` | account or org avatar (not the repo), 512×512, κ on blue |
| `avatar-dark.svg` | avatar variant, κ on ink |
| `avatar-light.svg` | avatar variant, κ on cream (light contexts) |
| `favicon.svg` | favicon, κ on blue, rounded |
| `favicon-cream.svg` | favicon variant, κ on cream (a light badge) |
| `favicon-dark.svg` | favicon variant, κ on ink (a dark badge) |
| `favicon-adaptive.svg` | transparent favicon; κ flips ink/cream with the OS theme |
| `social.svg` | repo social preview, 1280×640, cream |
| `social-blue.svg` | repo social preview, 1280×640, blue |
| `social-dark.svg` | repo social preview, 1280×640, ink |

Only the SVGs are versioned. GitHub needs raster (PNG) for avatars and social
previews, so export them from the SVGs when branding the repo (avatar 512×512,
social 1280×640) with any SVG renderer, e.g. `cairosvg`. The `*.png` exports are
gitignored.
