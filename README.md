# ELYSY to Karaoke ASS

Convert [ELYSY](https://github.com/gabrielxcom/ELYSY) **Enhanced SRT** (one timed cue per word) or **JSON** aligned lyrics into word-synchronized Advanced SubStation Alpha (ASS) karaoke subtitles for FFmpeg.

- Python 3.10+; **no Python dependencies**
- Word highlighting using actual ELYSY alignment timestamps
- YouTube landscape (1920 × 1080, lyrics on the right)
- TikTok vertical (1080 × 1920)
- Instagram Reels and Stories (1080 × 1920), and Instagram Feed portrait (1080 × 1350)
- Customizable font, line grouping, timing offsets, and subtitle position

## Quick start

Export **Enhanced SRT (word-by-word)** or **JSON (raw data)** from ELYSY after aligning the **final** audio file. Standard SRT has only line-level timestamps and is not a substitute for Enhanced SRT.

```bash
python3 elysy_to_karaoke_ass.py "The_Rangers_Promise_Clear_Rock_Remaster_enhanced-SRT.srt" \
  --profile wide --output lyrics-wide.ass
```

The repository includes Hank's user-provided Enhanced SRT at `tests/fixtures/The_Rangers_Promise_Clear_Rock_Remaster_enhanced-SRT.srt` for regression testing. The timestamp data is preserved unmodified.

## Presets

| Profile | Target | Dimensions | Default placement |
| --- | --- | --- | --- |
| `wide` | YouTube / landscape lyric panel | 1920 × 1080 | right |
| `vertical` | TikTok | 1080 × 1920 | center |
| `instagram-reels` | Instagram Reels | 1080 × 1920 | center, raised |
| `instagram-story` | Instagram Stories | 1080 × 1920 | center, raised |
| `instagram-feed` | Instagram Feed portrait | 1080 × 1350 | center, raised |

Run with whichever profile matches the **final video resolution**:

```bash
python3 elysy_to_karaoke_ass.py song-enhanced-SRT.srt --profile wide --output lyrics-wide.ass
python3 elysy_to_karaoke_ass.py song-enhanced-SRT.srt --profile vertical --output lyrics-tiktok.ass
python3 elysy_to_karaoke_ass.py song-enhanced-SRT.srt --profile instagram-reels --output lyrics-reels.ass
python3 elysy_to_karaoke_ass.py song-enhanced-SRT.srt --profile instagram-story --output lyrics-story.ass
python3 elysy_to_karaoke_ass.py song-enhanced-SRT.srt --profile instagram-feed --output lyrics-feed.ass
```

### JSON (recommended for exact lyric-line grouping)

```bash
python3 elysy_to_karaoke_ass.py song-JSON.json --profile wide --output lyrics-wide.ass
```

ELYSY Enhanced SRT contains word timings but not original lyric-line boundaries. The converter groups its word cues by gaps, punctuation, and configurable length limits. JSON exports preserve the original line groupings.

## FFmpeg: render lyric videos

Install an FFmpeg build with the libass `ass` filter. Check:

```bash
ffmpeg -hide_banner -filters | grep ' ass '
```

### YouTube, landscape 1920 × 1080

Use a 16:9 background that places artwork on the left, leaving the right side free for subtitles.

```bash
ffmpeg -y -loop 1 -framerate 30 \
  -i background-wide.png -i song.mp3 \
  -vf "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,ass=lyrics-wide.ass" \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 320k -shortest karaoke-youtube.mp4
```

### Instagram Reels and Stories, portrait 1080 × 1920

```bash
ffmpeg -y -loop 1 -framerate 30 \
  -i background-vertical.png -i song.mp3 \
  -vf "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,ass=lyrics-reels.ass" \
  -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p \
  -c:a aac -b:a 256k -shortest karaoke-reels.mp4
```

For TikTok, use the `vertical` profile. For Instagram Feed, generate `lyrics-feed.ass` and change both the scaling/cropping resolution to `1080:1350`.

Instagram UI overlays vary; always preview on-device before posting.

## Troubleshooting missing input files

If a file isn't found, the converter now prints a short error rather than a Python traceback:

```text
Error: File not found: 'song.srt'. Check the filename and directory, or provide an absolute path.
```

Verify the file is in your current Terminal directory (`pwd`, then `ls -l`) or supply its complete path. **The file must exist exactly as named**, including capitalization and any `(1)` suffix added by the browser when downloading duplicates. Invalid SRT/JSON files and output write failures also produce concise errors and a nonzero exit status.

## Settings

```bash
python3 elysy_to_karaoke_ass.py --help
```

| Option | Meaning |
| --- | --- |
| `--profile` | Select destination platform/layout |
| `--output FILE`, `-o FILE` | Output ASS path (defaults to input with `.ass`) |
| `--font NAME` | Subtitle font (default `Arial`) |
| `--placement right\|center` | Place lyrics on right (ideal for Hank's landscape art) or center |
| `--offset SECONDS` | Positive = later, negative = earlier |
| `--max-words N` | SRT words per displayed line (default 7) |
| `--max-chars N` | SRT maximum text length per displayed line |
| `--max-span SECONDS` | SRT maximum displayed line duration |
| `--gap SECONDS` | Pause threshold that starts a new lyric line |
| `--hold SECONDS` | Extra time a completed line remains visible |
| `--bottom PIXELS` | Override subtitle bottom margin |

Examples:

```bash
# Shift lyrics only when an intro was added AFTER alignment:
python3 elysy_to_karaoke_ass.py song.srt --profile wide --offset 4.8

# Shorter Instagram phrases:
python3 elysy_to_karaoke_ass.py song.srt --profile instagram-reels \
  --max-words 5 --max-chars 30 --gap 0.8 --output reels.ass

# Center the lyrics on a widescreen video:
python3 elysy_to_karaoke_ass.py song.srt --profile wide --placement center
```

If ELYSY analyzed the final audio **including** its intro, use `--offset 0` (the default).

## Development and testing

Use the project's **local META testing environment** (`chatgpt-dev` / `chatgpt-build-02`) rather than GitHub-hosted runners.

```bash
python3 -m py_compile elysy_to_karaoke_ass.py
python3 -m unittest discover -s tests -v

# Optional FFmpeg integration check:
ffmpeg -hide_banner -filters | grep ' ass '
```

The checked-in `tests/fixtures/sample_enhanced.srt` is a **synthetic fixture**. The real `tests/fixtures/The_Rangers_Promise_Clear_Rock_Remaster_enhanced-SRT.srt` contains **181 timed words**, starting at **00:01:30.337** and ending at **00:02:42.076**. The converter successfully retains all 181 word tags in its output. However, **153 words have identical 0.320-second durations**; treat the export as a parser regression fixture, *not* proof that lyric timestamps are synchronized to the recording. Recheck alignment in ELYSY while playing the final audio.

## Limitations

- Word timing accuracy depends on the ELYSY alignment.
- Enhanced SRT does not preserve original lyric line groupings; prefer ELYSY JSON when possible.
- Burn ASS subtitles into video with FFmpeg for consistent appearance across social platforms.
