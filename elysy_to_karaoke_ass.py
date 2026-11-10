#!/usr/bin/env python3
"""Convert ELYSY Enhanced SRT (word cues) or ELYSY JSON to ASS karaoke.

No dependencies outside Python's standard library.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

TIME_RE = re.compile(
    r"(?P<start>\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})\s*-->\s*"
    r"(?P<end>\d{1,2}:\d{2}:\d{2}[,.]\d{1,3})"
)


@dataclass
class Word:
    text: str
    start: float
    end: float


def parse_time(value: str) -> float:
    h, m, s = re.split(r":", value)
    return int(h) * 3600 + int(m) * 60 + float(s.replace(",", "."))


def ass_time(seconds: float) -> str:
    cs = max(0, round(seconds * 100))
    h, rem = divmod(cs, 360000)
    m, rem = divmod(rem, 6000)
    s, c = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{c:02d}"


def escape_ass(value: str) -> str:
    return (value.replace("\\", "\\\\")
                 .replace("{", "\\{")
                 .replace("}", "\\}")
                 .replace("\n", " "))


def parse_srt(path: Path) -> list[Word]:
    raw = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    words = []
    for block in re.split(r"\n\s*\n", raw):
        lines = [s.strip() for s in block.splitlines() if s.strip()]
        idx = next((i for i, item in enumerate(lines) if TIME_RE.search(item)), None)
        if idx is None or idx + 1 >= len(lines):
            continue
        m = TIME_RE.search(lines[idx])
        text = " ".join(lines[idx + 1:]).strip()
        if text:
            start, end = parse_time(m["start"]), parse_time(m["end"])
            words.append(Word(text, start, max(end, start + .01)))
    if not words:
        raise ValueError("No timed words found. Export Enhanced SRT from ELYSY.")
    return sorted(words, key=lambda w: w.start)


def parse_json(path: Path) -> list[list[Word]]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(data, dict):
        data = data.get("lines", data.get("aligned_lines", []))
    if not isinstance(data, list):
        raise ValueError("Expected ELYSY's exported JSON list of aligned lines.")
    output = []
    for line in data:
        if not isinstance(line, dict):
            continue
        row = []
        for word in line.get("words", []):
            if not isinstance(word, dict):
                continue
            label = str(word.get("word", word.get("text", ""))).strip()
            start = word.get("start", word.get("startSec"))
            end = word.get("end", word.get("endSec"))
            if label and start is not None:
                start = float(start)
                end = max(float(end) if end is not None else start + .3, start + .01)
                row.append(Word(label, start, end))
        if row:
            output.append(sorted(row, key=lambda w: w.start))
    if not output:
        raise ValueError("No word timestamps found in ELYSY JSON export.")
    return output


def group_srt(words: list[Word], max_words: int, max_span: float,
              gap: float, max_chars: int) -> list[list[Word]]:
    groups = []
    current = []
    for word in words:
        if current and (word.start - current[-1].end > gap
                        or len(current) >= max_words
                        or len(" ".join(w.text for w in current)) + len(word.text) + 1 > max_chars
                        or word.end - current[0].start > max_span):
            groups.append(current)
            current = []
        current.append(word)
        if re.search(r"[.!?]$", word.text) and len(current) >= 2:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def karaoke_words(group: list[Word]) -> str:
    """Use real word start/end times; gaps become unsung spacing tags."""
    result = []
    cursor = group[0].start
    for i, word in enumerate(group):
        if word.start > cursor + .015:
            gap_cs = max(1, round((word.start - cursor) * 100))
            result.append(f"{{\\k{gap_cs}}}")
        next_start = group[i + 1].start if i + 1 < len(group) else word.end
        stop = min(word.end, next_start) if next_start > word.start else word.end
        duration_cs = max(1, round((stop - word.start) * 100))
        spacer = " " if i else ""
        result.append(f"{{\\kf{duration_cs}}}{spacer}{escape_ass(word.text)}")
        cursor = max(stop, word.start)
    return "".join(result)


PROFILES = {
    "wide": (1920, 1080, 90, 59),
    "vertical": (1080, 1920, 310, 59),
    "instagram-reels": (1080, 1920, 440, 54),
    "instagram-story": (1080, 1920, 380, 54),
    "instagram-feed": (1080, 1350, 230, 51),
}


def make_ass(groups: list[list[Word]], profile: str, font: str,
             offset: float, bottom: int, hold: float, placement: str) -> str:
    wide = profile == "wide"
    width, height, _, base_size = PROFILES[profile]
    size = (46 if placement == "right" else 67) if wide else base_size
    margin = bottom
    alignment = 3 if placement == "right" else 2
    margin_l = 1040 if wide and placement == "right" else 75
    margin_r = 85 if wide and placement == "right" else 75
    header = f"""[Script Info]
Title: ELYSY word-synced karaoke
ScriptType: v4.00+
WrapStyle: 2
ScaledBorderAndShadow: yes
PlayResX: {width}
PlayResY: {height}

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Karaoke,{font},{size},&H00F5D27B,&H00FFFFFF,&H00201510,&H85000000,1,0,0,0,100,100,0,0,1,4,1,{alignment},{margin_l},{margin_r},{margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for i, group in enumerate(groups):
        start = max(0, group[0].start + offset)
        next_start = (groups[i+1][0].start + offset) if i + 1 < len(groups) else float('inf')
        end = min(group[-1].end + offset + hold, next_start - .02)
        end = max(start + .08, end)
        text = karaoke_words(group)
        events.append(
            f"Dialogue: 0,{ass_time(start)},{ass_time(end)},Karaoke,,0,0,0,,{text}"
        )
    return header + "\n".join(events) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="ELYSY *enhanced-SRT.srt or *JSON.json")
    parser.add_argument("--output", "-o", type=Path, help="Output ASS filename")
    parser.add_argument(
        "--profile", choices=tuple(PROFILES), default="wide",
        help="wide=YouTube, vertical=TikTok, instagram-reels/story/feed=Instagram safe zones",
    )
    parser.add_argument("--font", default="Arial", help="Installed font family")
    parser.add_argument("--placement", choices=("right", "center"), default=None,
                        help="Wide: right lyric panel by default. Vertical: center by default.")
    parser.add_argument("--offset", type=float, default=0.0,
                        help="Global time shift in seconds (e.g., 4.8 for an added intro)")
    parser.add_argument("--max-words", type=int, default=7,
                        help="Maximum words per displayed line for Enhanced SRT")
    parser.add_argument("--max-chars", type=int, default=None,
                        help="Maximum characters per line when grouping Enhanced SRT")
    parser.add_argument("--max-span", type=float, default=4.0,
                        help="Maximum line span, seconds")
    parser.add_argument("--gap", type=float, default=.65,
                        help="Split at pauses longer than this, seconds")
    parser.add_argument("--hold", type=float, default=.25,
                        help="How long to retain a completed line, seconds")
    parser.add_argument("--bottom", type=int, default=None,
                        help="Bottom margin in pixels (defaults depend on profile)")
    args = parser.parse_args()
    placement = args.placement or ("right" if args.profile == "wide" else "center")
    max_chars = args.max_chars or (38 if placement == "right" else (35 if args.profile.startswith("instagram") else 55))
    if args.input.suffix.lower() == ".json":
        groups = parse_json(args.input)
    elif args.input.suffix.lower() == ".srt":
        groups = group_srt(parse_srt(args.input), args.max_words,
                           args.max_span, args.gap, max_chars)
    else:
        parser.error("Input must be ELYSY Enhanced SRT (.srt) or ELYSY JSON (.json)")
    target = args.output or args.input.with_suffix(".ass")
    bottom = args.bottom if args.bottom is not None else PROFILES[args.profile][2]
    target.write_text(make_ass(groups, args.profile, args.font,
                               args.offset, bottom, args.hold, placement), encoding="utf-8-sig")
    print(f"Wrote {target} ({len(groups)} karaoke lines, {args.profile})")


if __name__ == "__main__":
    try:
        main()
    except FileNotFoundError as exc:
        print(
            f"Error: File not found: {exc.filename!r}. "
            "Check the filename and directory, or provide an absolute path.",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
    except (PermissionError, IsADirectoryError) as exc:
        print(f"Error: Cannot access file: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
    except (UnicodeError, ValueError) as exc:
        print(f"Error: Invalid input: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
    except OSError as exc:
        print(f"Error: File operation failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from None
