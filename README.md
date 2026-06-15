# Interactive Deep Notes

An agent skill that turns a **YouTube video** or a **web article** into a single,
self-contained interactive HTML page that teaches the source's ideas and helps
you actually *apply* them, not just re-read a summary.

Give your coding agent a URL and ask for interactive notes. The skill fetches the
source (video transcript via `yt-dlp`, or article text via `r.jina.ai`), then
designs a page tailored to that specific source with explanations, charts,
diagrams, flashcards, quizzes, action plans, and other interactive elements.

Every page is built to do four things, in order:

1. **Cover** every main point in the source.
2. **Explain** each idea deeply (the "why", not just the "what").
3. **Test** understanding with active recall (flashcards, quizzes, cloze, ...).
4. **Apply** it: turn each idea into something you do in your own life
   (action plans, if-then intentions, reflection prompts, trackers).

The output is one `index.html` file with inline CSS/JS and a `localStorage`-backed
store, so it opens straight from disk and your answers persist across reloads.

## Install

The easiest way is the [Skills CLI](https://skills.sh), which detects your agent
and drops the skill in the right place:

```bash
npx skills add risonsimon/interactive-deep-notes
```

### Manual install (git clone)

Or drop the skill folder into wherever your agent looks for skills.

**Claude Code** (`~/.claude/skills/`):

```bash
git clone https://github.com/risonsimon/interactive-deep-notes \
  ~/.claude/skills/interactive-deep-notes
```

**Cursor / project-local** (an `.agents/skills/` folder in your repo):

```bash
git clone https://github.com/risonsimon/interactive-deep-notes \
  .agents/skills/interactive-deep-notes
```

The agent reads `SKILL.md` and follows it from there.

## Requirements

The only thing you need installed is **[`uv`](https://docs.astral.sh/uv/)**. The
fetch script declares its Python version and `yt-dlp` as PEP 723 inline metadata,
so `uv run` builds an isolated environment automatically — it **downloads a
managed Python if you don't have one** and installs `yt-dlp` itself. No system
Python, no manual `pip install`, no virtualenv.

Don't have uv yet? Install it (then restart your shell, or `source
$HOME/.local/bin/env`, so it's on `PATH`):

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# macOS (Homebrew alternative)
brew install uv

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

You'll also need internet access: YouTube for video transcripts and
`https://r.jina.ai` for article text.

## Usage

The intended flow is to ask your agent for notes on a URL and let it follow
`SKILL.md`. Under the hood, step 1 is the fetch script, which you can also run
yourself:

```bash
# writes notes/<slug>/ (transcript.txt or content.md, plus meta.json) under the current dir
uv run scripts/fetch_source.py "https://www.youtube.com/watch?v=..."
uv run scripts/fetch_source.py "https://example.com/some-article"
```

Useful flags:

- `--type video|article` — force the kind (auto-detected from the URL host by default).
- `--out-dir DIR` — where to write the per-source folder (default `./notes`).
- `--cookies-from-browser brave` — for gated/age-restricted videos.
- `--force` — re-download even if cached.

The agent then builds `notes/<slug>/index.html` from the fetched source. Open
that file in a browser.

## What's in here

```
SKILL.md                 the skill the agent follows (workflow + quality bar)
reference/
  pedagogy.md            learn -> understand -> test -> apply; per source-type guidance
  components.md          copy-adaptable HTML/CSS/JS for every interactive element
  design.md              palette variety, typography, layout, motion
scripts/
  fetch_source.py        fetches a video transcript or article into notes/<slug>/
```

## Optional: a companion site (login + cross-device sync)

This skill grew out of a small Vercel site that serves the pages with a login
gate and per-user data sync (an `/app.js` store backed by Upstash Redis) plus a
generated home-page listing. None of that is required — pages are fully
self-contained on their own. If you want cross-device sync, you can swap the
inline `store` for a server-backed one without touching any component; see the
"companion site" callout in [`reference/components.md`](reference/components.md) (§0).

## License

[MIT](LICENSE)
