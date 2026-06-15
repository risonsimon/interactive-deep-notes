# Design direction

The page should look like it was made *for this source*, not stamped from a
template. This file is self-sufficient; it covers palette, typography, layout,
and motion for deep-notes pages.

## Optional: the impeccable skill (brand register)

If you have the **impeccable** skill installed, use it for the craft: read
`~/.claude/skills/impeccable/SKILL.md` and `reference/brand.md`, then run its
quick context/voice step before you style anything. It governs typography
procedure, spacing, hierarchy, and the absolute bans; this file then overrides
palette/typography *defaults* so every page looks different. Don't have it? The
rules below stand on their own — just follow them directly.

## The anti-default rule (read this twice)

You have a strong, repeated bias toward **dark espresso/brown backgrounds with
amber/gold accents**. Do not ship that again unless the source's subject truly
demands it (and even then, justify it).

Before designing, write down the palette and font pairing you'd reach for by
reflex. Then reject it and choose something that fits *this* source's subject and
emotional tone. Rotate across pages.

### How to choose a palette

1. Name the subject domain (money, grief, code, fitness, history, art, science…).
2. Name the emotional tone (calm, urgent, playful, sober, hopeful, clinical…).
3. Pick light vs dark from the tone: dark for intimate/intense/technical, light
   for instructional/optimistic/reference. Don't default to dark.
4. Choose a hue family that *means* something for the subject, plus one accent.
   Keep it to ~2 accents max.

### Ready-made palettes (none are brown/gold — rotate through these)

| Mood / subject | bg | surface | text | muted | accent | accent 2 |
|---|---|---|---|---|---|---|
| Clinical / science (light) | `#f7f9fb` | `#ffffff` | `#0f172a` | `#51607a` | `#2563eb` | `#0891b2` |
| Calm / mindful (light) | `#f3f6f2` | `#fbfdfb` | `#1f2a26` | `#5b6b63` | `#2f7d63` | `#7aa6c2` |
| Energetic / motivational (light) | `#ffffff` | `#fbf7fb` | `#161616` | `#5a5560` | `#e0245e` | `#6b4eff` |
| Nature / health (light) | `#f2faf5` | `#ffffff` | `#0f2a1d` | `#4a6b59` | `#16a34a` | `#0ea5e9` |
| Creative / arts (light) | `#faf7ff` | `#ffffff` | `#1a1430` | `#5d5575` | `#7c3aed` | `#db2777` |
| Serious / philosophy (cool stone) | `#eef1f4` | `#ffffff` | `#1f2933` | `#5b6776` | `#334155` | `#b91c1c` |
| Technical / code (dark) | `#0d1117` | `#161b22` | `#e6edf3` | `#8b949e` | `#58a6ff` | `#3fb950` |
| Introspective / night (dark indigo) | `#12121f` | `#1b1b2e` | `#e8e8f0` | `#9a9ab0` | `#8b7cf6` | `#4dd0c4` |
| Financial / business (deep navy) | `#0b1f33` | `#12263a` | `#eaf1f8` | `#8fa3b8` | `#14b8a6` | `#60a5fa` |

These are starting points. Shift hues, build proper tints/shades, and check
contrast (text on bg ≥ 4.5:1). Set them as CSS variables so charts/Mermaid
inherit them.

```css
:root { --bg:#…; --surface:#…; --text:#…; --muted:#…; --border:#…; --accent:#…; --accent-2:#…; }
```

## Typography

Follow impeccable's font procedure. Pick a display face that fits the subject
and a comfortable reading face for the long prose. Avoid the reflex-reject
defaults (Inter, Roboto, Open Sans, Lato, Montserrat, Poppins) as your primary,
and do not use Fraunces. Starting pairings that pass:

- Editorial / serious — **Newsreader** display + **Public Sans** or **Source Serif 4** body.
- Technical — **Space Grotesk** headings + **Spline Sans** body + mono accents (**IBM Plex Mono**).
- Calm / reflective — **Newsreader** italic display + **Literata** body.
- Bold / creative — **Bricolage Grotesque** + **Familjen Grotesk**.
- Science / explainer — **Spline Sans** + **IBM Plex Serif**.

One display + one reading face is plenty. Vary the pairing per source.

## Layout

- A single hero that states the thesis in one line, plus context (author or
  speaker, source/site, length or read time) and a clear "start" cue. Make it
  specific to the source.
- Prose in a reading column ~62–72ch. Don't run text full-bleed.
- Sticky chapter rail on desktop; collapsible on mobile. Generous vertical
  rhythm between sections; let it breathe.
- Build mobile-first and verify at 375px width. Interactives must work on touch.

## Motion

Restrained and purposeful. Subtle reveal-on-scroll, gentle state transitions.
No motion that delays reading. Always honor `prefers-reduced-motion` (see
components.md). Animation is seasoning, not the meal.

## Bans (in addition to impeccable's)

- The espresso/brown + amber/gold default palette (the whole point above).
- Cloning another note's structure or component set. The page's shape and its
  interactions come from this source's type and subject (see SKILL.md).
- Em dashes in copy. Use commas, colons, periods, or parentheses.
- Left side-stripe accent cards as the only structural device.
- Generic gradient-filled headline text.
- Glassmorphism/drop-shadow soup; one cohesive elevation system instead.
- Emoji as section icons unless the subject genuinely invites a playful voice.
