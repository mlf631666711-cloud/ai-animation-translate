# AI Animation Translate

[中文](README.md) · [English](README.en.md)

把已经剪好的中文动画换成英文版：英文配音、英文字幕、一份能在剪映里直接打开的草稿。
剪辑点、版式框、标题条、logo、音效、BGM 都留在原处。

**它做的事**：换三条轨（语音 / 语音下的画面 / 字幕），其余不动。
**它不做的事**：不重排镜头，不改剪辑节奏，不替你做翻译决定。
**给谁用**：要把一条成片出多语言版本的剪辑或自动化流程；也写给 agent 读。

## 快速开始

```bash
python tools/check_env.py                                  # 环境自检
python tools/jianying/inventory.py --draft "<中文草稿>" --json work/inventory.json
python tools/tts.py --segments work/segments.json --voice en-US-JennyNeural --out work/tts
python tools/cues_from_words.py --durations work/tts/_durations.json --inventory work/inventory.json --out work/cues_en.json
python tools/jianying/relanguage.py --master "<中文草稿>" --name "<英文草稿>" --en-draft "<素材草稿>" --cues work/cues_en.json --anim shot1_en
python tools/jianying/audit_language.py --draft "<英文草稿>"
```

七步的判据、产物和返工点见 [docs/pipeline.zh.md](docs/pipeline.zh.md)。

**用之前先读 [docs/playbook.zh.md](docs/playbook.zh.md)。** 这里的失败大多是静默的：时间轴全绿但没声音，文字塞得下但最后一笔被裁掉。

## 两种做法

| | A · 最小侵入换语言 | B · 重建时间轴 |
|---|---|---|
| 适用 | 同一支片换语言，剪辑已完成 | 从零拼新片 |
| 底 | 母版原时间轴，一条不删 | 母版目录骨架 + 新时间线 |
| 改动 | 语音轨 · 语音下的画面 · 字幕轨 | 内容整体替换 |
| 脚本 | `tools/jianying/relanguage.py` | `tools/jianying/rebuild_draft.py` |

A 是默认。只有当片子本来就要重排时才用 B。

## 目录

```
AGENTS.md                 给 agent 的入口：约束 + 命令 + 症状索引
docs/
  playbook.zh.md / .en.md 开工必读：每条规则对应一次真实翻车
  pipeline.zh.md / .en.md 七步流程与判据
  bugs.zh.md / .en.md     缺陷库（46 条）
  剪映草稿-规格与坑.md    剪映草稿的目录结构、素材箱、三处 id
tools/
  check_env.py            环境自检
  tts.py                  分段 TTS + 词级时间戳 + 时长表
  cues_from_words.py      按词轴切字幕
  render_frames.cjs       逐帧渲染（4K = --dpr 2）
  scan_times.py           时刻语法扫描（重锚完备性）
  jianying/
    inventory.py          翻译前盘点：字幕 / 配音 / 轨号
    relanguage.py         最小侵入换语言
    rebuild_draft.py      克隆母版 → 换内容 → 自检
    audit_language.py     收尾体检（七项，PASS/FAIL）
    audit_media.py        素材路径 / 素材箱 / id 一致性
    swap_draft.py         换名 + 写索引
    _jc/                  草稿加解密（Apache-2.0，来源见 THIRD-PARTY.md）
```

## 已知限制

- 草稿加密依赖剪映本体的 `videoeditor.dll`，Windows 为主；换大版本可能要重新定位偏移。
  默认取安装目录下版本号最高的一个，可用 `--jianying-install` 指定。
- 词级比对（字幕文字 vs 语音念词）需要 TTS 词轴；`audit_language.py` 里这一项显式跳过，写法在 playbook §10。
- 只覆盖单文件 HTML 动画 + 剪映草稿这条链路，不处理实拍素材的换语言。
- 片长与母版一致是硬约束。英文装不下时先压静音和间隙，不靠拉长片子解决。

## 文档

| 中文 | English |
|---|---|
| [开工必读](docs/playbook.zh.md) | [Field manual](docs/playbook.en.md) |
| [七步流程](docs/pipeline.zh.md) | [One-pass pipeline](docs/pipeline.en.md) |
| [缺陷库](docs/bugs.zh.md) | [Bug library](docs/bugs.en.md) |
| [剪映草稿规格](docs/剪映草稿-规格与坑.md) | — |
| [上游改动说明](docs/对上游的修改.md) | — |
| [操作手册](docs/操作手册.md) | — |

## 许可

本仓库代码 MIT，见 [LICENSE](LICENSE)。`tools/jianying/_jc/` 是 `jy-draftc` 的 Python 移植，
沿用 Apache-2.0，许可副本在该目录内。
