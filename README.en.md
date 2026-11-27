# AI Animation Translate

[中文](README.md) · [English](README.en.md)

Turn a finished Chinese motion film into an English cut: English voice, English subtitles, and a Jianying
draft that opens as-is. Cuts, layout frames, titles, logos, sound effects and BGM stay where the editor put them.

**What it does:** replaces three tracks — voice, the picture under the voice, subtitles. Nothing else.
**What it doesn't do:** re-order shots, change the edit rhythm, or make translation decisions for you.
**Who it's for:** editors shipping one film in several languages, and agents that run the pipeline.

## Quick start

```bash
python tools/check_env.py                                  # environment check
python tools/jianying/inventory.py --draft "<Chinese draft>" --json work/inventory.json
python tools/tts.py --segments work/segments.json --voice en-US-JennyNeural --out work/tts
python tools/cues_from_words.py --durations work/tts/_durations.json --inventory work/inventory.json --out work/cues_en.json
python tools/jianying/relanguage.py --master "<Chinese draft>" --name "<English draft>" --en-draft "<asset draft>" --cues work/cues_en.json --anim shot1_en
python tools/jianying/audit_language.py --draft "<English draft>"
```

Gates, outputs and rework points for the seven steps: [docs/pipeline.en.md](docs/pipeline.en.md).

**Read [docs/playbook.en.md](docs/playbook.en.md) before using it.** Most failures here are silent: timing
passes but there is no audio, text fits but the last letter is cropped.

## Two ways to work

| | A · Minimal relanguage | B · Rebuild the timeline |
|---|---|---|
| Use when | same film, new language, edit is finished | building a new film from scratch |
| Base | the master's original timeline, no track removed | master folder as skeleton + your timeline |
| Changes | voice track · picture under the voice · subtitle track | content replaced wholesale |
| Script | `tools/jianying/relanguage.py` | `tools/jianying/rebuild_draft.py` |

A is the default. Use B only when the film is being re-cut anyway.

## Layout

```
AGENTS.md                 entry point for agents: constraints, commands, symptom index
docs/
  playbook.zh.md / .en.md rules, each tied to a real failure
  pipeline.zh.md / .en.md the seven-step run and its gates
  bugs.zh.md / .en.md     46 collected failures
  剪映草稿-规格与坑.md    Jianying draft layout, material bin, id consistency
tools/
  check_env.py            environment check
  tts.py                  segmented TTS + word timestamps + duration table
  cues_from_words.py      subtitle splitting from the word axis
  render_frames.cjs       frame-by-frame render (4K = --dpr 2)
  scan_times.py           timestamp syntax scan for re-anchoring
  jianying/
    inventory.py          pre-translation inventory: subtitles / voice / tracks
    relanguage.py         minimal relanguage
    rebuild_draft.py      clone master → replace content → self-check
    audit_language.py     seven final checks, PASS/FAIL
    audit_media.py        material paths / bin / id consistency
    swap_draft.py         rename + write index
    _jc/                  draft crypto (Apache-2.0, see THIRD-PARTY.md)
```

## Known limits

- Draft encryption calls Jianying's own `videoeditor.dll`; Windows first. A major version bump may need new
  offsets. The tool picks the highest version found under the install root; override with `--jianying-install`.
- Word-level comparison (subtitle text vs spoken words) needs TTS word timings. `audit_language.py` skips that
  check explicitly; the recipe is in playbook §10.
- Covers the single-file HTML animation + Jianying draft path only. No live-action relanguage.
- Runtime parity with the master is a hard constraint. If English doesn't fit, compress silence and gaps —
  do not lengthen the film.

## Docs

| Chinese | English |
|---|---|
| [开工必读](docs/playbook.zh.md) | [Field manual](docs/playbook.en.md) |
| [七步流程](docs/pipeline.zh.md) | [One-pass pipeline](docs/pipeline.en.md) |
| [缺陷库](docs/bugs.zh.md) | [Bug library](docs/bugs.en.md) |
| [Jianying draft spec](docs/剪映草稿-规格与坑.md) | — |
| [Upstream changes](docs/对上游的修改.md) | — |
| [Operations manual](docs/操作手册.md) | — |

## License

Code: MIT, see [LICENSE](LICENSE). `tools/jianying/_jc/` is a Python port of `jy-draftc`, Apache-2.0;
the license copy sits in that folder.
