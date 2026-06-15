#!/usr/bin/env python
# /// script
# requires-python = ">=3.11"
# dependencies = ["yt-dlp"]
# ///
"""Fetch the source for an interactive deep-notes page: a video transcript OR an article.

Run it with uv -- the only prerequisite. The inline PEP 723 metadata below makes
`uv run` provision an isolated environment automatically: it downloads a managed
Python if none is installed and installs yt-dlp. No system Python or pip needed.

    uv run scripts/fetch_source.py "<url>"

The type is auto-detected from the URL (known video hosts -> video, else article).
Force it with --type video|article. Writes a per-source folder into the output
dir (default ./notes):

    video:    notes/<slug>/transcript.txt   timestamped plain text ([HH:MM:SS] markers)
    article:  notes/<slug>/content.md       clean markdown from https://r.jina.ai/<url>
    both:     notes/<slug>/meta.json        includes "type": "video" | "article"

These files are the regeneration source: the interactive HTML page is built from
them into notes/<slug>/index.html, and can be rebuilt any time.

Prints a JSON summary (the paths + key metadata) to stdout so the agent can
parse it directly.
"""

import argparse
import glob
import json
import os
import re
import sys
import tempfile
import unicodedata
import urllib.parse
import urllib.request
from urllib.error import HTTPError, URLError

# Per-source folders are written under ./notes by default (relative to wherever
# you run the script). Override with --out-dir.
DEFAULT_OUT_DIR = "notes"

# Hosts that should be treated as videos in --type auto. Everything else is an
# article fetched through r.jina.ai. yt-dlp supports far more sites than this;
# pass --type video to force any other host down the transcript path.
VIDEO_HOSTS = {
    "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be", "youtube-nocookie.com",
    "vimeo.com", "player.vimeo.com", "dailymotion.com", "www.dailymotion.com",
    "twitch.tv", "www.twitch.tv", "ted.com", "www.ted.com",
}


# --- VTT -> timestamped text ------------------------------------------------
# Keep full HH:MM:SS on each cue start so the HTML can build "jump to this
# moment" deep links.

def remove_tags(text: str) -> str:
    for pat in (r"</c>", r"<c(\.color\w+)?>", r"<\d{2}:\d{2}:\d{2}\.\d{3}>"):
        text = re.sub(pat, "", text)
    # cue header: "00:01:23.456 --> 00:01:25.000 ..."  ->  "00:01:23"
    text = re.sub(r"(\d{2}:\d{2}:\d{2})\.\d{3} --> .*", r"\g<1>", text)
    text = re.sub(r"^\s+$", "", text, flags=re.MULTILINE)
    return text


def remove_header(lines: list[str]) -> list[str]:
    pos = -1
    for mark in ("##", "Language: en"):
        if mark in lines:
            pos = lines.index(mark)
    return lines[pos + 1:]


def merge_duplicates(lines: list[str]):
    last_ts, last_cap = "", ""
    for line in lines:
        if line == "":
            continue
        if re.match(r"^\d{2}:\d{2}:\d{2}$", line):
            if line != last_ts:
                yield line
                last_ts = line
        elif line != last_cap:
            yield line
            last_cap = line


def convert_vtt_to_text(vtt: str, chunk_chars: int = 240) -> str:
    """Group cues into readable paragraphs, each prefixed with [HH:MM:SS]."""
    text = remove_tags(vtt)
    lines = list(merge_duplicates(remove_header(text.splitlines())))

    out: list[str] = []
    chunk_ts: str | None = None
    buf: list[str] = []
    for line in lines:
        if re.match(r"^\d{2}:\d{2}:\d{2}$", line):
            if buf and len(" ".join(buf)) >= chunk_chars:
                out.append(f"[{chunk_ts}] " + " ".join(buf).strip())
                chunk_ts, buf = line, []
            elif chunk_ts is None:
                chunk_ts = line
        else:
            buf.append(line)
    if buf:
        out.append(f"[{chunk_ts}] " + " ".join(buf).strip())
    return "\n\n".join(out).strip()


# --- helpers ----------------------------------------------------------------

def sanitize_filename(name: str, fallback: str = "notes") -> str:
    name = "".join(
        c for c in unicodedata.normalize("NFKD", name) if not unicodedata.combining(c)
    ).lower()
    name = re.sub(r"[^a-z0-9]+", "-", name).strip("-")
    return name[:120] or fallback


def human_duration(seconds) -> str:
    if not seconds:
        return ""
    seconds = int(seconds)
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def pick_vtt(tmp_dir: str) -> str | None:
    files = glob.glob(os.path.join(tmp_dir, "*.vtt"))
    if not files:
        return None
    # Prefer manual English (".en.vtt") over auto / other tracks.
    for key in (".en.vtt", ".en-US.vtt", ".en-GB.vtt", "en"):
        for f in files:
            if key in os.path.basename(f):
                return f
    return files[0]


def detect_type(url: str) -> str:
    host = (urllib.parse.urlparse(url).hostname or "").lower()
    return "video" if host in VIDEO_HOSTS else "article"


def short_description(markdown: str, limit: int = 280) -> str:
    """First real paragraph of the article, cleaned of markdown noise."""
    for block in re.split(r"\n\s*\n", markdown):
        text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", block)     # drop images (alt + url)
        text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)   # links -> their text
        text = re.sub(r"[#*_`>]+", " ", text)                  # strip md marks (keep hyphens)
        text = re.sub(r"^\s*[-\u2022]+\s*", "", text)          # leading bullet
        text = re.sub(r"\s+", " ", text).strip()
        if len(text) >= 40:
            return text if len(text) <= limit else text[: limit - 1].rstrip() + "\u2026"
    return ""


# --- article via r.jina.ai --------------------------------------------------

def fetch_article_text(url: str, timeout: int = 90) -> str:
    """GET https://r.jina.ai/<url> and return the raw reader response (markdown)."""
    reader_url = "https://r.jina.ai/" + url
    req = urllib.request.Request(
        reader_url,
        headers={
            "User-Agent": "Mozilla/5.0 (interactive-deep-notes fetcher)",
            "Accept": "text/plain, text/markdown, */*",
            "X-Return-Format": "markdown",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_jina(raw: str) -> dict:
    """Pull Title / URL Source / Published Time out of the reader header, and
    return the markdown body separately."""
    out = {"title": None, "url_source": None, "published_time": None, "markdown": raw}

    def grab(label: str) -> str | None:
        m = re.search(rf"^{label}:\s*(.+)$", raw, flags=re.MULTILINE)
        return m.group(1).strip() if m else None

    out["title"] = grab("Title")
    out["url_source"] = grab("URL Source")
    out["published_time"] = grab("Published Time")

    marker = re.search(r"^Markdown Content:\s*$", raw, flags=re.MULTILINE)
    if marker:
        out["markdown"] = raw[marker.end():].lstrip("\n")
    return out


# --- main -------------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("url", help="a video URL (yt-dlp supported) or an article URL")
    ap.add_argument(
        "--type",
        choices=["auto", "video", "article"],
        default="auto",
        help="source kind; auto detects from the URL host (default: auto)",
    )
    ap.add_argument(
        "--out-dir",
        default=DEFAULT_OUT_DIR,
        help="where to write the per-source folder (default: ./notes)",
    )
    ap.add_argument(
        "--cookies-from-browser",
        default=None,
        help="(video only) browser to read cookies from (e.g. brave, chrome) for gated videos",
    )
    ap.add_argument("--force", action="store_true", help="re-download even if cached")
    args = ap.parse_args()

    out_dir = os.path.abspath(os.path.expanduser(args.out_dir))
    os.makedirs(out_dir, exist_ok=True)

    source_type = args.type if args.type != "auto" else detect_type(args.url)

    if source_type == "article":
        return run_article(args, out_dir)
    return run_video(args, out_dir)


def run_video(args, out_dir: str) -> int:
    from yt_dlp import YoutubeDL

    base_opts: dict = {"quiet": True, "no_warnings": True}
    if args.cookies_from_browser:
        base_opts["cookiesfrombrowser"] = (args.cookies_from_browser,)

    # 1) metadata only -> title, id, slug, cache check
    with YoutubeDL({**base_opts, "skip_download": True}) as ydl:
        info = ydl.extract_info(args.url, download=False)

    slug = sanitize_filename(info.get("title") or info.get("id") or "video", "video")
    video_dir = os.path.join(out_dir, slug)
    os.makedirs(video_dir, exist_ok=True)
    transcript_path = os.path.join(video_dir, "transcript.txt")
    meta_path = os.path.join(video_dir, "meta.json")

    subtitle_source = "cached"
    if args.force or not os.path.exists(transcript_path):
        # 2) download subtitles into a temp dir, then clean + persist
        with tempfile.TemporaryDirectory() as tmp:
            sub_opts = {
                **base_opts,
                "skip_download": True,
                "writesubtitles": True,
                "writeautomaticsub": True,
                "subtitleslangs": ["en", "en-US", "en-GB", "en-orig"],
                "subtitlesformat": "vtt",
                "outtmpl": os.path.join(tmp, "%(id)s.%(ext)s"),
            }
            with YoutubeDL(sub_opts) as ydl:
                ydl.download([args.url])

            vtt = pick_vtt(tmp)
            if not vtt:
                print(
                    "ERROR: no English subtitles found for this video. "
                    "The video may have captions disabled. Try --cookies-from-browser brave, "
                    "or transcribe the audio separately.",
                    file=sys.stderr,
                )
                return 1

            subtitle_source = "manual" if bool(info.get("subtitles", {}).get("en")) else "automatic"
            with open(vtt, "r", encoding="utf-8") as f:
                transcript = convert_vtt_to_text(f.read())

        with open(transcript_path, "w", encoding="utf-8") as f:
            f.write(transcript)

    meta = {
        "title": info.get("title"),
        "slug": slug,
        "type": "video",
        "video_id": info.get("id"),
        "url": info.get("webpage_url") or args.url,
        "channel": info.get("channel") or info.get("uploader"),
        "uploader": info.get("uploader"),
        "upload_date": info.get("upload_date"),
        "duration_seconds": info.get("duration"),
        "duration_readable": human_duration(info.get("duration")),
        "view_count": info.get("view_count"),
        "thumbnail": info.get("thumbnail"),
        "tags": info.get("tags") or [],
        "categories": info.get("categories") or [],
        "description": info.get("description"),
        "chapters": info.get("chapters") or [],
        "subtitle_source": subtitle_source,
        "source_file": "transcript.txt",
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    html_path = os.path.join(out_dir, slug, "index.html")
    print(json.dumps({
        "slug": slug,
        "type": "video",
        "source_dir": video_dir,
        "source_path": transcript_path,
        "source_file": "transcript.txt",
        "meta_path": meta_path,
        "html_output_path": html_path,
        "title": meta["title"],
        "channel": meta["channel"],
        "duration": meta["duration_readable"],
        "video_id": meta["video_id"],
        "url": meta["url"],
        "subtitle_source": subtitle_source,
    }, ensure_ascii=False, indent=2))
    return 0


def run_article(args, out_dir: str) -> int:
    # 1) fetch the reader output first so we can title -> slug from it
    try:
        raw = fetch_article_text(args.url)
    except (HTTPError, URLError, TimeoutError) as e:
        print(
            f"ERROR: could not fetch the article through r.jina.ai ({e}). "
            "Check the URL, your connection, or try again in a moment.",
            file=sys.stderr,
        )
        return 1

    parsed = parse_jina(raw)
    markdown = parsed["markdown"].strip()
    if len(markdown) < 80:
        print(
            "ERROR: r.jina.ai returned little or no article text. The page may be "
            "paywalled, JS-only, or blocking the reader. Try a different URL.",
            file=sys.stderr,
        )
        return 1

    host = (urllib.parse.urlparse(args.url).hostname or "").lower()
    site = host[4:] if host.startswith("www.") else host
    title = parsed["title"] or site or "article"
    slug = sanitize_filename(title, "article")

    article_dir = os.path.join(out_dir, slug)
    os.makedirs(article_dir, exist_ok=True)
    content_path = os.path.join(article_dir, "content.md")
    meta_path = os.path.join(article_dir, "meta.json")

    if args.force or not os.path.exists(content_path):
        with open(content_path, "w", encoding="utf-8") as f:
            f.write(markdown + "\n")

    word_count = len(markdown.split())
    meta = {
        "title": title,
        "slug": slug,
        "type": "article",
        "url": parsed["url_source"] or args.url,
        "channel": site,              # shown on the home card like a video's channel
        "site": site,
        "author": None,
        "published_time": parsed["published_time"],
        "upload_date": None,
        "word_count": word_count,
        "read_minutes": max(1, round(word_count / 220)),
        "thumbnail": None,
        "description": short_description(markdown),
        "source_file": "content.md",
    }
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    html_path = os.path.join(out_dir, slug, "index.html")
    print(json.dumps({
        "slug": slug,
        "type": "article",
        "source_dir": article_dir,
        "source_path": content_path,
        "source_file": "content.md",
        "meta_path": meta_path,
        "html_output_path": html_path,
        "title": meta["title"],
        "channel": meta["site"],
        "site": meta["site"],
        "url": meta["url"],
        "word_count": word_count,
        "read_minutes": meta["read_minutes"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
