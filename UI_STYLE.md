# Meraklis — UI Style Guide

Adopted 2026-05-31. **Applies to all future frontend work** (`frontend/src`). When
creating or editing any UI, follow these rules. The previous look was "cliché and
oily" — high-contrast, glowy, with rounded outline chips that read as fake buttons.
We are moving to a calm, flat, professional aesthetic.

## Aesthetic direction
Flat and quiet, like **Windows 8 / early Windows Phone "Metro"**: solid colour
fills, flat rectangles, minimal borders, clear typography. No glow, no oily
gradients, no decorative neon.

## Rules

### 1. Minimize outlines/borders on buttons
- Remove light-colour outlines from the **majority** of buttons.
- Keep an outline / strong emphasis **only for vital actions** — the primary CTA and
  decision/destructive actions. Examples: "Start analysing" / "Investigate",
  "Cancel selection", "Approve".
- Everything else is borderless: a flat fill or plain text button.

### 2. Indicators must never look like buttons
- Remove circular / pill borders (outline rings) from **non-clickable** indicators
  and labels — e.g. `TOOL`, `RESULT`, status chips (`OFFLINE`/`ONLINE`), icon badges,
  count pills.
- Replace them with **clean plain solid colour fills** — flat rectangles, Metro-style.
  No rounded pills, no outline rings for static content.
- Clickable vs non-clickable must be unambiguous: **only clickable things may look
  interactive.** If it isn't a button, it must not look like one.

### 3. Colour scheme — white/grey, low contrast, professional
- Base palette is **mainly white and grey.** Use colour sparingly and purposefully
  (e.g. a single accent for the primary action or a genuine risk signal).
- Cut high-contrast / neon accents (the bright-green glow especially).
- Fewer, clearer **icons and status indicators**; remove decorative or confusing ones.
- Default to quiet and professional over flashy.

## Do / Don't
- **Don't:** glowing borders, rounded pill chips for static labels, neon green
  everywhere, decorative animated bars, ambiguous icon badges, fake/synthetic
  telemetry widgets.
- **Do:** flat solid fills, generous white/grey, borders reserved for the primary or
  destructive action, legible type, one restrained accent colour used intentionally.

## Notes
- Living document — update as the design system evolves.
- When in doubt: if a reviewer can't tell at a glance whether something is clickable,
  or the screen feels "loud," it's wrong.
