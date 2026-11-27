# One Pass · Chinese Film to English Cut

[中文](pipeline.zh.md) · [English](pipeline.en.md)

One command per step. Each step has an artefact and a gate. Seven steps produce a Jianying draft you can open.

```
env → copy → inventory → voice → subtitles → relanguage → audit
```

The first five steps never touch the edit. Only the last two write to it. **If a gate fails, stop.**

## 0 Environment

```bash
python tools/check_env.py          # prints install commands for whatever is missing
```

Requires Python ≥ 3.9, Node, Chrome, ffmpeg/ffprobe, and Jianying (draft encryption uses its `videoeditor.dll`).

## 1 Segmented copy

```json
{ "segments": [
  { "id": "s01", "shot": 1, "text": "Racing fans, look here!" },
  { "id": "s02", "shot": 1, "text": "Two columns, eight levels.", "read": "optional TTS-only spelling" }
] }
```

Split rule: a sentence ending in `. ! ?` is its own segment; a line ending in a comma, colon or dash is a
typographic wrap and merges with the next line.

## 2 Inventory the Chinese master

```bash
python tools/jianying/inventory.py --draft "<Chinese draft>" --json work/inventory.json
```

One row per subtitle: index / time / text / matching voice (track + time + material). Look for three things:

- **How many tracks the voice lives on.** Reading only the longest track misses segments — a real case
  missed 10 of 29, producing a half-Chinese cut that passed every timing check.
- **Subtitles with no voice.** Those are on-screen labels; they follow picture, not speech.
- **Same-track overlap.** The Chinese original allows cross-track overlap; only same-track overlap is a fault.

Gate: unmatched rows read `none`. If you can't explain each `none`, do not start translating.

## 3 Synthesize

```bash
python tools/tts.py --segments work/segments.json --voice en-US-JennyNeural --out work/tts
```

| File | Use |
|---|---|
| `s01.mp3` / `s01.wav` | 48 kHz mono, ready for the draft |
| `s01.words.json` | word timestamps, for subtitle breaks |
| `_durations.json` | real duration per segment, for scheduling |
| `joined.wav` | one file to listen to |

Gate: total duration ≤ the Chinese master's matching span. If it overflows, compress in this order —
trim trailing silence, shrink gaps, raise the rate (≤ +15%). Don't rewrite the copy first.

## 4 Cut subtitles

```bash
python tools/cues_from_words.py --durations work/tts/_durations.json \
    --inventory work/inventory.json --out work/cues_en.json
```

Breaks come from word timestamps, not character counts. Rules in [playbook §5](playbook.en.md).
The output is absolute-time `[{t0,t1,text}]`, ready for the next step.

Gate: longest line ≤ 65 characters; every break lands at a sentence end or comma; no trailing periods.

## 5 Relanguage

```bash
python tools/jianying/relanguage.py \
  --master "<Chinese draft>" \
  --name   "<English draft name>" \
  --en-draft "<English asset draft>" \
  --cues   work/cues_en.json \
  --anim   shot1_en,shot2_en
```

It changes three things only: the voice track, the subtitle track, and the picture under the voice.
Cuts, layout frames, titles, logos, SFX and BGM stay where the editor put them.

Gate: runtime equals the master (unless a segment is explicitly deleted); every replaced clip starts at
the same timecode as its Chinese counterpart.

## 6 Audit

```bash
python tools/jianying/audit_language.py --draft "<English draft>"
```

Seven checks; only `PASS` counts. Failures print the specific segments (which one has no subtitle,
which line runs past its voice, where the overlap is).

Two manual checks on top:

- `python tools/jianying/audit_media.py --draft "<English draft>"` — material paths, bin, id consistency.
- Sample three frames: opening, the frame with the most text, the end card. Text must sit ≥ 40 px from the edges.

## Common rework

| Symptom | Check first |
|---|---|
| No sound | Is the new audio material `extract_music`? Does the path contain `..`? Is the video `volume=0`? |
| Subtitles half a sentence off | Did subtitles copy Chinese timing? Did the TTS cache reuse an old line? |
| Whole film a few seconds late | Trailing silence trimmed? Were multiple tracks scheduled as one sequence? |
| Render shows the cover or a progress bar | Does the page have a bare mode? Did `--query` reach the main render path? |
| Text outside the frame | Were coordinates derived from Chinese character counts? Re-measure after translation. |
