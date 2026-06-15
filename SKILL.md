---
name: interactive-deep-notes
description: >-
  Turn a YouTube video OR a web article into a single self-contained interactive
  HTML page that teaches its ideas and helps the user APPLY them in real life.
  Fetches the source (video transcript via yt-dlp, or article text via
  r.jina.ai), then builds a custom, well-designed page with explanations, charts,
  tables, flashcards, quizzes, action plans and other interactive elements. Use
  when the user gives a video or article URL and asks for interactive notes, a
  study/learning page, flashcards, or a way to understand and apply its lessons.
---

# Interactive Deep Notes

Turn a video or an article into a single self-contained HTML page the user can
open, learn from, be tested by, and act on.

## North star: application, not just notes

The user's real goal is **to change how they live/work after consuming it**, not
to re-read a summary. Pure recall is a means; the end is transfer. Every page
must do four things, in order:

1. **Cover** every main point in the source. Miss nothing important.
2. **Explain** each idea with enough depth to truly understand it (the "why",
   not just the "what").
3. **Test** understanding with active recall (flashcards, quizzes, self-checks).
4. **Apply** it: turn each idea into something the user does in their own life
   (action plans, if-then plans, reflection prompts, trackers).

If a section only informs but never asks the user to recall or act, it is not
done. See [reference/pedagogy.md](reference/pedagogy.md) for the model.

## Design each page from its source (don't clone the last one)

The pages keep coming out near-identical for one reason: it's tempting to open
an earlier note's `index.html` and refill the same skeleton. **Don't.** Do not
read another note's built HTML to learn "the format" or to copy its structure or
its set of interactive elements. There is no canonical format to match, and
copying siblings is the exact habit that makes every page feel the same.

Only the **shell** is shared across pages:

- the floating TOC rail (scroll-spy + reading progress),
- the link back to the source (video -> a "Watch video" button + the video in a
  modal; article -> a "Read original" button), and
- the inline `store` that persists the reader's answers (see components.md §0).

Everything *inside* that shell is decided fresh for this source: the section arc,
which interactive elements appear, how many, and in what order. A tutorial, a
debate, a grief essay, and a market explainer should not share a skeleton.

So before you build, name two things and let them drive the page:

1. **What kind of source is this?** (lecture, tutorial, coaching call, interview,
   debate, documentary/explainer, sales pitch, essay, news analysis, ...) Each
   kind wants a different structure and different interactions.
2. **What should the user be able to *do* afterward?** Design backward from that.

Then deliberately reach for a different mix of elements than recent notes used.
If you find yourself defaulting to the same deck + quiz + if-then + reflection on
every source, stop: that's templating, not teaching. Use the breadth in
[reference/components.md](reference/components.md) and invent elements the
content calls for.

## Inputs

- A **video URL** (usually YouTube) or a **web article URL**. Or a path to an
  existing `notes/<slug>/` source folder (`transcript.txt` or `content.md`).
- Optional steer from the user (depth, audience, focus, length, mood).

The fetch script auto-detects video vs article from the URL; you can force it.

## Where things live

Everything for one source lives in a single self-contained folder,
`notes/<slug>/`:

- `notes/<slug>/meta.json` — metadata, including `"type": "video" | "article"`.
- `notes/<slug>/transcript.txt` (video) **or** `notes/<slug>/content.md`
  (article) — the **source text**. Keep it so the page can be regenerated later.
- `notes/<slug>/index.html` — the **built page**. It's fully self-contained
  (inline CSS/JS + a `localStorage` store), so the reader just opens this file.

The fetch script (step 1) creates this folder and prints the exact paths.

> **Optional companion site.** This skill grew out of a small Vercel site that
> serves the pages under `/notes/<slug>` with login + cross-device sync (an
> `/app.js` store backed by Upstash Redis) and a generated home-page listing.
> None of that is required — a page stands on its own. If you *are* building into
> such a site, see the companion-site callout in components.md §0.

## Workflow

```
- [ ] 1. Fetch the source (transcript or article) + metadata (script)
- [ ] 2. Read everything; build the learning spine
- [ ] 3. Plan structure: map each point -> understand + test + apply
- [ ] 4. Pick a design direction (vary the palette; don't clone the last note)
- [ ] 5. Build one self-contained HTML file with rich interactives
- [ ] 6. Open in a browser, verify, polish
- [ ] 7. Save the note folder
```

### 1. Fetch the source

**Preflight — the only prerequisite is `uv`.** The script declares its Python
version and `yt-dlp` as inline (PEP 723) metadata, so `uv run` builds an isolated
environment on the fly: it **downloads a managed Python if the machine doesn't
have one** and installs `yt-dlp` itself. The user needs neither Python nor
`yt-dlp` pre-installed — only `uv`.

So check for `uv` first and install it if missing. Detect the user's OS and run
the matching command (don't run all of them):

```bash
uv --version    # if this prints a version, skip the install below

# macOS / Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
# macOS with Homebrew (alternative):
brew install uv
# Windows (PowerShell):
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

After a fresh install, `uv` may not be on `PATH` until a new shell is started;
`source $HOME/.local/bin/env` (macOS/Linux) exposes it in the current shell. If
`uv` still isn't found, tell the user and stop rather than guessing.

Then run the fetch from the directory where you want the `notes/` output (the
script path is relative to this skill folder; videos use `yt-dlp`, articles use
`r.jina.ai`):

```bash
uv run scripts/fetch_source.py "<url>"   # writes notes/<slug>/ under the current dir
```

The first `uv run` may take a few seconds while it provisions Python and
`yt-dlp`; later runs are cached and fast.

It auto-detects the kind from the URL host (YouTube/Vimeo/etc. -> video, any
other host -> article) and writes a `notes/<slug>/` folder:

- **Video** -> `transcript.txt` (timestamped paragraphs like `[00:04:12] ...`)
  plus `meta.json` (`type: "video"`, title, channel, duration, video id,
  thumbnail, description, chapters).
- **Article** -> `content.md` (clean markdown from `https://r.jina.ai/<url>`)
  plus `meta.json` (`type: "article"`, title, site, url, published time, word
  count, read minutes, description).

It prints a JSON summary that includes `slug`, `type`, the source paths, and
`html_output_path` (where you'll write the built page).

- Force the kind with `--type video` or `--type article` (e.g. a video on a host
  the detector doesn't know, or an article on a video host).
- Video flags: `--cookies-from-browser brave` for gated videos.
- `--out-dir DIR` to change location, `--force` to re-download.
- If a video reports no subtitles, tell the user (captions may be disabled). If
  an article comes back near-empty (paywalled / JS-only), tell the user instead
  of inventing content.

### 2. Read everything; build the learning spine

Read the **entire** source (the transcript or the article markdown, and the
`description` in meta.json for resources it references). Do not skim. Then write
a short internal outline:

- **Thesis**: the one sentence the piece is really about.
- **Main points**: every distinct idea, claim, framework, step, or story. Be
  exhaustive: this is the "cover everything" guarantee.
- **Concepts**: terms/models that need a real definition to understand.
- **Q&A / objections**: if it's a coaching call, interview, AMA, or debate,
  capture each question and its answer.
- **Evidence & numbers**: any data, study, or figure (you'll chart real numbers
  only; never fabricate).
- **Actions**: everything the author/speaker tells the reader to do or try.
- **Anchors**: for **videos**, keep the `[HH:MM:SS]` timestamps so you can
  deep-link moments. For **articles**, note section headings / memorable lines so
  you can quote and link back to the original.

### 3. Plan the structure (fresh for this source)

Start by naming the **source type** and the **capability** the user should walk
away with (the two questions above). The structure follows from those, not from
a fixed template. Use pedagogy.md's per-type guidance to shape both the section
arc and the interactions: lecture/talk, tutorial/how-to, coaching/therapy,
interview/podcast, debate, documentary/explainer, sales/pitch, essay/long-read,
and news/analysis each lean on a different shape and a different element set.

Group the spine into a handful of sections that follow the source's arc (or a
cleaner teaching order; the number and naming of sections is yours to decide).
For **each main point**, decide three things:

- How to **explain** it (prose, concept card, diagram, comparison, analogy, ...).
- How to **test** it (flashcard, MCQ, cloze, self-explain, match/order, ...).
- How to **apply** it (action item, if-then plan, reflection, tracker, scenario,
  decision practice, ...).

Then pick the interactive elements that genuinely fit *this* content — the
content->component cheat sheet in pedagogy.md is the map. Choose a set that
differs from recent notes; don't reuse the same widgets out of habit, and don't
force a point into a widget that doesn't suit it.

### 4. Pick a design direction

Read [reference/design.md](reference/design.md) for the visual system (palette
variety, typography, layout, motion). If you also have the **impeccable** skill
installed (`~/.claude/skills/impeccable/SKILL.md`, brand register), use it for
the craft — it's a nice-to-have, not a requirement. The hard rule:

> Do **not** default to the dark espresso/brown + amber/gold palette. Choose a
> palette and typography that come from *this* source's subject and mood. Rotate
> deliberately; design.md has ready alternatives.

### 5. Build the HTML

Write the page to **`notes/<slug>/index.html`** (use the `html_output_path` from
step 1). Put all CSS in a `<style>` tag and the page-specific JS in a `<script>`
tag; fonts from Google Fonts (or a system stack). External JS libs only via CDN
(`<script src>`), and only when they earn their place (e.g. Chart.js for charts,
Mermaid for diagrams). The page must be **self-contained**: it should open
straight from disk with no server.

Drop in the small persistence foundation from `reference/components.md` §0 — a
slug-keyed `localStorage` `store` plus `wireSaves`/`exportNotes` — and wire it
before the rest of your page JS:

```html
<!-- optional: keep the page out of search engines -->
<meta name="robots" content="noindex, nofollow" />
<script>
const SLUG = "<slug>";              // the folder name; namespaces saved answers
const store = createStore(SLUG);    // sync get/set, persists to localStorage
document.addEventListener("DOMContentLoaded", () => {
  wireSaves(store);                 // auto-save/restore every [data-save] field
  // ...then wire your decks / quizzes / habits / nav / video modal.
});
</script>
```

See `reference/components.md` §0 for the full
`createStore`/`wireSaves`/`exportNotes` snippet (and the optional path that backs
the store with a server for cross-device sync).

[reference/components.md](reference/components.md) is a **parts bin, not a
checklist**. Do not pour every widget onto every page. Pick the few that truly
fit this source, and make the set noticeably different from the last note. You
are not limited to that list — build elements the content calls for.

Two parts are the same on every page (this is the shared shell):

- **Orientation:** sticky chapter rail + scroll-spy, reading progress, and a
  clear link back to the original. For a **video**, a "Watch video" button (under
  the TOC) opens it in a modal, and timestamp buttons open that same modal seeked
  to the moment. For an **article**, a "Read original article" button links out
  to the source URL (new tab); use plain section anchors instead of timestamps.
- **Persistence:** every `data-save` field, deck, quiz and habit saves through
  the `store` above; offer an "export my answers" button
  (`exportNotes("Title", "file.md")`) and a clean print stylesheet.

Everything else is your call, driven by the source type. The page must still do
three jobs (north star), but choose forms that fit the content and vary them
across notes:

- **Understand** — concept cards, annotated quotes, comparison tables, charts
  (real data only), diagrams / timelines / cycles, "go deeper" details, or a
  bespoke visual for this subject.
- **Test (active recall)** — at least one mechanism, and not always the same one:
  flashcards, an MCQ quiz, cloze, a "say it back" self-explain box, a match /
  order exercise, a myth-vs-fact toggle.
- **Apply** — at least one mechanism the user acts on: an editable action plan,
  if-then intentions, a reflection journal, a habit tracker, a decision / scenario
  practice, a "where do you land?" slider, a self-assessment scorecard.

Let the material lead. A few illustrations (don't copy them as a template):

- **Tutorial / how-to:** ordered steps with checkboxes, a copyable checklist or
  template, "try it now" prompts; flashcards for the gotchas.
- **Debate / two-sided:** a side-by-side argument table + a position slider with
  a reasoning box; a quiz that tests steelmanning each side.
- **Coaching / self-help:** reframe flip-cards (belief -> truer belief), a
  reflection journal, if-then plans; light on quizzes.
- **Documentary / data explainer:** charts for the real figures, a timeline, a
  myth-vs-fact set, a scorecard.
- **Interview / podcast:** theme-grouped pull-quotes with commentary, flashcards
  on the guest's key claims, a "which of these will you try?" picker.

Match the elements to the content instead of fitting the content into a stock
layout.

Build the file incrementally with `Write` then `StrReplace` (a single huge
`Write` can fail to serialize). Respect `prefers-reduced-motion` and keep it
keyboard-accessible. Content is sacred: every claim must trace back to the
source (transcript or article); never invent facts, quotes, or numbers.

That's the whole page. (If you're building into the optional companion site,
also run its `bun run build` so the new note appears on the home-page listing.)

### 6. Verify lightly (do it yourself, no subagents)

Keep this quick. Do **not** spawn subagents (browser-use or otherwise) and do
**not** run an exhaustive QA pass. The page is self-contained, so just open
`notes/<slug>/index.html` in a browser. If your browser restricts `localStorage`
on `file://`, serve the folder instead (using `uv run python` so you don't need a
system Python):

```bash
uv run python -m http.server 8765 --directory notes   # then visit /<slug>/
```

A short self-check is enough: open it once, click a flashcard and a quiz option,
reload to confirm a saved answer persists, and confirm the "watch/read original"
link works (for a video, that the modal opens at a timestamp). **Then narrow the
window to phone width and check the chrome:** the watch/read button must be
reachable (the rail is hidden, so the floating bottom-right copy is what you tap),
and the sticky "Jump to" bar must not slide off-screen. Fix anything obviously
broken. The patterns in components.md are already proven, so trust them instead
of re-testing every element.

### 7. Save the note folder

The page is just files under `notes/<slug>/`. Save or commit them however the
project you're in expects. If it's a git repo, stage this note's folder and
commit with a clear message — and stick to the usual safety rules (never
force-push, never amend a commit you didn't create this session, don't touch the
git config). If a push is rejected or there's no upstream, report it rather than
forcing anything.

## Output conventions

- Built page: `notes/<slug>/index.html` (open it directly; fully self-contained).
- Source kept for regeneration: `notes/<slug>/meta.json` plus `transcript.txt`
  (video) or `content.md` (article), in the same folder.
- Never delete or overwrite another note's folder.
- The page is self-contained: inline CSS/JS plus a `localStorage` store, no
  server required. (Backing the store with a server for cross-device sync is
  optional; see components.md §0.)
- Save the note folder as the last step (workflow step 7).

## Quality bar (check before finishing)

- [ ] Every main point from the source is present (spot-check against the text).
- [ ] Each key idea is explained deeply enough to actually understand it.
- [ ] The structure and element set were chosen for THIS source's type — not
      copied from another note, and not the same default mix every time.
- [ ] At least one active-recall mechanism and one application mechanism, in
      forms that fit the content (vary them; they need not be flashcards + quiz).
- [ ] Each major idea has a concrete "do this in your life" application.
- [ ] Page is at `notes/<slug>/index.html`; source kept in the same folder.
- [ ] `meta.json` has the right `"type"` (`video` or `article`).
- [ ] Creates the store from the slug (components.md §0) and wires saves before use.
- [ ] A link back to the original works (video modal / "read original" button),
      and it's reachable on mobile — a floating bottom-right copy, since the rail
      (and its watch button) is hidden on phones.
- [ ] Sticky mobile bars stay on-screen (reserve `padding-right` for any
      top-right control; nothing tappable hidden under it).
- [ ] User inputs/progress persist (via the store); answers are exportable.
- [ ] Page is fully self-contained and opens straight from disk (no server).
- [ ] Design is custom and fits the subject; palette is NOT the brown/gold default.
- [ ] Works on mobile, respects reduced-motion, decent contrast.
- [ ] No invented content; quotes and numbers are faithful to the source.
- [ ] Note folder saved (workflow step 7).

## Reference files

- [reference/pedagogy.md](reference/pedagogy.md) — the learn → understand →
  test → apply model, per source-type adaptation, content→component mapping.
- [reference/components.md](reference/components.md) — copy-adaptable code for
  flashcards, quizzes, charts, diagrams, action plans, persistence, export.
- [reference/design.md](reference/design.md) — palette variety (anti brown/gold
  bias), typography, layout, and motion.
