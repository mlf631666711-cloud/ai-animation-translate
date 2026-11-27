# Field Manual · English Version of a Chinese Edit

[中文](playbook.zh.md) · [English](playbook.en.md)

Written for whoever runs the pipeline — human or agent. Every rule below comes from a real failure. The bracketed ID points to an entry in the [bug library](bugs.en.md).

> Read order: this page → [one-key pipeline](pipeline.en.md) → the bugs. Not the other way round.

## 0. Three rules that override everything

1. **Duration belongs to the edit, not to you.** Every clip you replace must start at the same timecode as its Chinese counterpart (±10 ms). Overflow pushes the footage, subtitles and sound effects after it.
2. **Meaning never gives way to duration.** You may drop filler words and repeated phrasing. Verbs, qualifiers and numbers stay. If it still doesn't fit, compress with engineering (silence trim, gaps, rate) — then ask the owner before cutting meaning.
3. **Run the audit script before delivery.** "Looked fine" is not a check.

## 1. Translation unit

- Translate **whole semantic sentences**, not subtitle cells. Both the Chinese subtitles and the voice-over were chopped; merge first.
- Test: if reading it aloud leaves the thought unfinished, it is one sentence ("first the same-direction cable" + "to the board's MIPI_CSI port and the adapter").
- Splitting a finished sentence into subtitle cells is a layout job. Do it after translation, not during.
- Keep model names, units and numbers verbatim. Write English for speaking, not word-for-word gloss.

## 2. Inventory before translating

Skipping this produces the classic half-Chinese, half-English cut where every timing check still passes.

1. **List every Chinese subtitle.** Scan all text tracks, not just the longest one. Separate dialogue subtitles from on-screen labels.
2. **Find the matching voice for each line.** Voice segments may be spread over **several audio tracks**. Real case: 29 segments across three tracks (2 / 19 / 8). Reading only the longest track missed 10 segments.
3. **Decide ownership.** Each line is either dialogue (follows speech) or a label (follows picture). Their timing rules are different.
4. **Only then translate.** Subtitle count vs voice-segment count must reconcile; every difference needs an explanation.

**Gate:** print a table of `subtitle # / time / Chinese / matching voice segment (track + time)` before translating. Missing matches are marked `none`. No table, no translation.

## 3. Duration follows the Chinese cut

Compression order — use it in sequence, don't skip steps:

1. **Trim trailing silence per segment.** edge-tts leaves 0.77–0.80 s at the end of every segment; four segments is 3 s. Most overlooked, most effective.
2. **Shrink inter-sentence gaps.** 0.25 → 0.12 s. The Chinese original is nearly gapless.
3. **Raise the speech rate.** +10% by default, +13% if needed, +15% ceiling. Beyond that it sounds rushed.
4. **Warp the animation onto the Chinese timeline** so the picture runs at Chinese speed.
5. Still too long → go back and ask before cutting meaning.

**Gate:** print "English total vs Chinese duration" before rendering. It must be ≤. Otherwise do not render.

## 4. TTS

- English: edge-tts, `en-US-JennyNeural`. Chinese reference: Jianying's built-in read-aloud.
- Request word timestamps with `boundary='WordBoundary'`. The default is sentence level.
- Normalize loudness to −17 dB. Mono → stereo loses 3 dB: convert first, measure, then compensate.
- **Split acronyms into letters + word.** `PSRAM` is read letter by letter; write `P S ram` to get "pee ess ram". `P-S-ram` also fails (one token).
- **Never add `-v error` to `volumedetect`.** The stats are logged at info level and get swallowed; `mean_volume` returns garbage (seen: gain computed as +82 dB, output silent).
- **TTS cache key must include a hash of the text**: `v3_%02d_%s_%s.mp3 % (index, rate, md5(text)[:6])`. Keyed only by index + rate, an edited sentence still hits the old audio — voice says the old line, subtitles show the new one. Apply the same test anywhere an old file can masquerade as a new result.

## 5. Subtitles

- Break order: period > semicolon/colon > comma > clause start > before a prepositional phrase.
- Never break after an article, preposition, conjunction, "be" verb or intensifier. Never inside a noun phrase.
- Character count is a ceiling, not a reason to break. If you hit the ceiling mid-phrase, walk back to a legal break.
- English line ceiling: 65 characters (roughly the width of 21 full-width Chinese characters). Use the widest Chinese line in the same film as the reference.
- Place breaks using word timestamps, not proportional estimates.
- No space after commas, no trailing space, no period at the end of a subtitle cell. Keep model names, units and numbers intact.

## 6. Re-animating for English

Changing the text is not localization. The delivery criterion is **the animation follows the English voice**.

- Fixed order: Chinese sentence → English sentence → TTS (mp3 + word timestamps) → inline audio → re-time animation against the word axis.
- Re-time with a piecewise-linear `warp(x)`: `WP = [[english_time, chinese_time], …]`.
- `warp` must be monotonic, `warp(0)=0`, and the last point maps to the Chinese edited length.
- A global ratio `x * zh/en` only works for sections with no local rhythm difference. Where information density differs, split into segments — otherwise scenes change before or after the spoken word.
- Anchor scene boundaries to the nearest semantic word (show "Capture" when the word is said), not to a proportional timestamp.
- For films with hard-coded timeline modules: leave `VOICE` and frame counts alone, add the double mapping — English playback → Chinese edited time → existing `animationTime()`.
- After swapping audio, sample frames around each cut: picture must match what is being said.

## 7. Frame-boundary check

Text clipped by the frame is usually discovered after rendering — the most expensive kind of rework.

- **Re-measure width whenever the copy changes.** Any coordinate or font size derived from Chinese character counts or fixed pixels (e.g. `openingWidths`, `left = (1920 - ...) / 2`) must become a runtime `offsetWidth` measurement, scaled down to fit. Centering without an overflow test will fail.
- **Look at the locked frame, not the middle of the shot.** Use `--stills <seconds>` and inspect the four edges — clipped elements are always at the edge.
- Criterion: text blocks ≥ 40 px from left/right, ≥ 24 px from top/bottom. Boards and images must not be cut.
- Sample the frame with the most text, not a uniform spread.

## 8. Single-file HTML has two copies of its JS

In a single-file deliverable the JS is inlined, while an external `.js` often still sits in the folder. A build script that edits the external file produces nothing but silence — rendering reads the inlined copy.

- At the end of the build, sync `EN_FRAMES`, `WP` and the render function into the HTML and grep them back.
- Before rendering, `grep "const EN_FRAMES" <html>` must equal the build's printed value; after rendering, `ffprobe` duration must equal frames / 30.

## 9. Rendering and the edit

- **Single-file HTML with a player must run in bare mode.** Otherwise the render bakes in the cover play button, the Play bar or the progress bar. Convention: `?t=<seconds>` (stills) or `?export` (full film) adds `body.bare`, with `body.bare #ctl/cover/.tools { display:none }`. Verify the renderer's `--query` flag actually reaches the main render path — it once only reached the stills path.
- **A `.preview` container fixed at 1320 px will crop the 1920 stage.** Export mode must also stretch the container to 1920×1080.
- **Always split audio out of a replaced video.** Set the video segment `volume=0`, extract the voice to a new narration track (never into an existing SFX track — they overlap). Jianying often ignores the audio track of an mp4 written by a script: `has_audio=True` and still no sound, visible as a flat waveform.
- **Three hard requirements for a new audio material** — miss one and it is silent, with no error:
  1. `type='extract_music'` (not `sound`; the SFX type does not read local files, waveform stays flat);
  2. path passed through `os.path.normpath`, no `..`;
  3. copy the segment template from a **known-good voice segment**, not from an SFX segment.
  Use mp3 (192k).
- **Anything added to the timeline must also be added to the material bin.** The bin is not in `draft_content.json`; it lives in two places:
  1. `draft_meta_info.json` → `draft_materials`, the `type=0` group (this file is encrypted; decrypt before writing);
  2. `draft_virtual_store.json` → `draft_virtual_store`, the `type=1` group; each material needs `{child_id, parent_id: ""}`, or it won't appear at the bin root.
  Entry fields: `metetype` = `video` / `music`; audio `width/height = 0`; `md5` empty; `roughcut_time_range` = full clip.
- **Close Jianying before writing**, then sync `Timelines/<uuid>/draft_content.json`. Round-trip check before encryption; do not write if it differs.
- Encode scripts refuse to overwrite; save a new version number. Frames may be deleted, masters may not.

## 10. Final audit (mandatory)

Seven checks, all required:

1. Every voice segment is covered by subtitles (no "sound but no text").
2. First subtitle starts at voice start − 0.10 s (±0.30).
3. No subtitle extends past the end of its voice segment.
4. **Subtitle text ≈ the words actually spoken.** Normalize both to word sets; difference on words longer than 2 characters. More than 2 words missing on either side ⇒ FAIL, print the differing words.
5. No overlap between subtitle segments.
6. No overlap between voice segments.
7. Zero leftover Chinese voice (`text_to_audio`).

Two scheduling rules:

- **Trim trailing silence first**, otherwise "English is longer than Chinese" is an illusion.
- **Schedule per track, not as one global sequence.** Voice may live on several tracks and the Chinese original allows cross-track overlap; keep a cursor per track. The schedule table should contain no `pushed +x.xx`.

Old-draft trap: in `version=360000` drafts, every track has `type='mixed'` (no text/video/audio distinction), and **the first segment often omits `target_timerange.start`** (meaning 0). An audit that skips missing starts will report one row short.

## 11. Delivery

- Show an HTML preview first; render 4K only after it is approved.
- One 4K master (voice + SFX). No separate 1080p preview.
- Vertical versions are cropped by the platform; they are not part of the production flow.
- State the runtime, the replaced segment positions, and the rollback point (backup file name).
