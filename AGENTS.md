# AGENTS.md · how an agent should run this repo

[中文](AGENTS.zh.md) · [English](AGENTS.md)

This file is the entry point for an automated worker. Read it before touching anything, then read
`docs/playbook.en.md`. The playbook explains why each rule exists; this file tells you what to do.

## What this repo does

Turns a finished Chinese motion film into an English version: English voice, English subtitles, and a
Jianying draft that opens on the editor's machine with every cut, title, logo, SFX and BGM in place.

The unit of work is **one replaced shot inside an existing edit**, not a standalone film.

## Read order

| Order | File | Why |
|---|---|---|
| 1 | this file | constraints and commands |
| 2 | `docs/playbook.en.md` | the rules, each tied to a real failure |
| 3 | `docs/pipeline.en.md` | the seven-step run |
| 4 | `docs/bugs.en.md` | look up a symptom when something breaks |

Do not skip to the commands. The failure modes in this repo are silent: timing passes, audio is missing;
text fits, the last letter is cropped.

## Hard constraints

1. **Never re-time the film.** Replaced clips keep the Chinese segment's start and duration (±10 ms).
   Runtime changes only when a whole segment is added or removed. Re-timing moves the editor's footage,
   subtitles and sound effects.
2. **Never delete meaning to save time.** Verbs, qualifiers, numbers stay. Compress silence, gaps and rate first.
3. **Every audio material is `extract_music`, mp3 192k, normalised path (no `..`).** Anything else is silent,
   with no error.
4. **Split audio out of replaced videos.** Video `volume=0`; voice on its own track.
5. **A page with a player must render in bare mode** (`?t=` / `?export`). Otherwise the cover button or the
   progress bar ends up in the film.
6. **Measure text at runtime.** Coordinates derived from Chinese character counts overflow in English.
7. **Run the audit before saying it is done.** `audit_language.py` must print `PASS`. "Looks right" is not a check.

## The run

```bash
python tools/check_env.py
python tools/jianying/inventory.py --draft "<Chinese draft>" --json work/inventory.json
python tools/tts.py --segments work/segments.json --voice en-US-JennyNeural --out work/tts
python tools/cues_from_words.py --durations work/tts/_durations.json --inventory work/inventory.json --out work/cues_en.json
python tools/jianying/relanguage.py --master "<Chinese draft>" --name "<English draft>" --en-draft "<assets draft>" --cues work/cues_en.json --anim shot1_en
python tools/jianying/audit_language.py --draft "<English draft>"
```

Gates, in order: inventory table has no unexplained `none` → English total ≤ Chinese span → longest subtitle
≤ 65 chars → runtime equals master → audit `PASS`.

## Where to look when it breaks

| Symptom | Entry |
|---|---|
| Voice missing, flat waveform | DB-33 |
| Subtitles ahead of or behind the voice | DB-36 |
| Subtitle text differs from what is spoken | DB-37 |
| Everything runs a few seconds late | DB-38 |
| Render starts with a play button | DB-31 |
| Text cropped at the frame edge | DB-42 |
| Build says 21 s, video says 25 s | DB-44 |
| Film longer than the Chinese cut | DB-43 |
| Opening line has no verb | DB-39 |
| Translation logic inverted (`or`, manual vs auto) | DB-40 |

## Do not

- Do not run `relanguage.py` against the editor's only copy. Copy the draft directory first; Jianying must
  be closed or sitting on its home screen before writing.
- Do not invent paths or filenames. Read `work/inventory.json` and the draft's material list.
- Do not "fix" a failing gate by loosening the gate. If a threshold is wrong, say so with a measurement.
- Do not add a dependency without updating `requirements.txt` / `package.json`.
- Do not translate on-screen labels with the dialogue track. Labels follow picture; dialogue follows speech.

## Definition of done

- `audit_language.py` prints `PASS` and exits 0.
- `audit_media.py` reports no missing paths and no orphan materials.
- Three frames checked: opening, densest text, end card. No text within 40 px of the frame edge.
- The deliverable states runtime, replaced segment positions, and the rollback path (backup file name).
