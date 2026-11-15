# Concept2 Logbook — logo and branding assets

Handover note for Claude Code. These files are **proposals, not yet wired in**.
Nothing in `custom_components/`, `README.md` or the design doc has been changed.
Per `CLAUDE.md`: present a plan first, wait for approval, and note that a
non-placeholder icon is a Gate 5 item in the design doc (check the gate status
before applying).

## Concept

The icon tells the journey of the data in one picture, read left to right:

1. **Row** — a generic rowing-machine silhouette (monorail, flywheel housing,
   seat, handle).
2. **Data is created** — the monitor above the flywheel shows a force curve
   (amber).
3. **Home Assistant fetches it** — three amber dots and a chevron lead to a plain
   house outline with an amber dot inside (the dot is the sensor/entity).

Legal care taken (not legal advice): no text in the mark, no "2", no Concept2,
PM5 or Home Assistant logo shapes, and no logo colours of either. The machine is
a generic silhouette and the house is a plain outline. Only the social preview
carries a name, and only as the repo URL.

Add to the README (suggested, not applied): "Not affiliated with or endorsed by
Concept2 or Nabu Casa / Home Assistant."

## Palette (same as the Kontoret/Lamper dashboards)

| Role | Value |
| --- | --- |
| Background | `#060a14` (near-black navy) |
| Structure / accent | `#64ffda` (turquoise) |
| Data / warm accent | `#ffb74d` (amber) |
| Glass card | white at 3.5 % fill, 9 % border |
| Light variant | navy `#0b1220`, dark amber `#b45309` on `#f3f8ff` |

Style: dark tile, slow colour blobs (turquoise top-left, amber bottom-right),
soft glow on the strokes, thin type (weight 200) with spaced small-caps labels.

## Files

| File | Size | Use |
| --- | --- | --- |
| `icon.svg` | 512×512 | Master source. Dark rounded tile with the full mark. |
| `icon.png` | 256×256 | HA brand `icon.png` |
| `icon@2x.png` | 512×512 | HA brand `icon@2x.png` |
| `icon-compact.svg` | 512×512 | Bold variant for sizes below 48 px |
| `icon-compact-64.png` | 64×64 | Preview of the compact variant |
| `icon-mark.svg` / `.png` | 440 viewBox / 880×880 | Mark only, transparent. **Dark backgrounds only** (turquoise is low contrast on white). |
| `social-preview.svg` / `.png` | 1280×640 | GitHub social preview |

The PNGs were rendered from the SVGs in Chromium. Edit the SVGs, then re-render;
do not edit the PNGs by hand. Text in `social-preview.svg` uses Inter and falls
back to Helvetica/Arial; install Inter before re-rendering.

## Where it goes (when approved)

1. **HA/HACS brand icon:** copy `icon.png` and `icon@2x.png` to
   `custom_components/concept2_logbook/brand/`. A placeholder `icon.png` already
   exists there, so overwrite it deliberately. HACS validation accepts this path
   (design doc, HACS brands note). Keep the tile background so the icon works on
   light and dark themes.
2. **README header:** the `<img>` at the top of `README.md` points at the same
   `brand/icon.png`. Update its `alt` text (it currently says "plain
   placeholder") and remove the placeholder notes at README (Known limitations,
   the line about the integration icon), CHANGELOG ("Integration icon is a plain
   placeholder") and the design doc HACS-brands paragraph.
3. **GitHub social preview:** upload `social-preview.png` under the repo's
   Settings, Social preview. This is a manual step in the GitHub UI.
4. **Optional:** submit to `home-assistant/brands` later; use the same PNGs.

Suggested commit style: `docs:` for README/CHANGELOG changes and `feat:` or
`docs:` for the asset files, with the attribution lines from the session
reminder.

## Small sizes

Use `icon.svg` from about 64 px and up. Below 48 px use `icon-compact.svg`
(fewer details, thicker strokes). The full icon is not legible at 16 px.

## Design source

The design lives on the Claude Design canvas "Concept2 Logbook – logo" (private).
It has the icon, the banner, and the A/B/C variants (A primary, B compact,
C light) with accent colours as tweaks. The SVGs here are the exported source of
truth for the repo.
