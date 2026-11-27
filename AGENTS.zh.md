# AGENTS.md · agent 怎么用这个仓库

[中文](AGENTS.zh.md) · [English](AGENTS.md)

自动化执行者先读这一页，再读 `docs/playbook.zh.md`。playbook 讲每条规则为什么存在，这一页讲做什么。

## 这个仓库干什么

把一条已经剪好的中文动画换成英文版：英文配音、英文字幕、一份能在剪映里打开的草稿。
剪辑点、标题、logo、音效、BGM 全部保留。

工作单位是**一条成片里的某个替换镜头**，不是一条独立的新片。

## 阅读顺序

| 顺序 | 文件 | 为什么 |
|---|---|---|
| 1 | 本页 | 约束与命令 |
| 2 | `docs/playbook.zh.md` | 规则，每条对应一次真实翻车 |
| 3 | `docs/pipeline.zh.md` | 七步流程 |
| 4 | `docs/bugs.zh.md` | 出问题时按症状查 |

不要直接跳到命令。这里的失败大多是静默的：时间轴全绿但没声音；文字塞得下但最后一笔被裁掉。

## 硬约束

1. **不许重排时间轴。** 替换段保持中文段的起点和时长（±10ms）。片长只在「整段新增/删除」时变化。
2. **不许为时长删语义。** 动词、限定词、数字要留；先压静音、间隙、语速。
3. **音频素材一律 `extract_music`、mp3 192k、路径过 `normpath`（不带 `..`）。** 否则静音且不报错。
4. **替换的视频要分离音频。** 视频 `volume=0`，语音单独一条轨。
5. **带播放器的页面必须走裸模式**（`?t=` / `?export`），否则封面按钮或进度条会进成片。
6. **文案宽度运行时实测。** 按中文字数算的坐标换成英文一定出画。
7. **说「做完」之前跑审计。** `audit_language.py` 必须输出 `PASS`。肉眼过一遍不算检查。

## 运行

```bash
python tools/check_env.py
python tools/jianying/inventory.py --draft "<中文草稿>" --json work/inventory.json
python tools/tts.py --segments work/segments.json --voice en-US-JennyNeural --out work/tts
python tools/cues_from_words.py --durations work/tts/_durations.json --inventory work/inventory.json --out work/cues_en.json
python tools/jianying/relanguage.py --master "<中文草稿>" --name "<英文草稿>" --en-draft "<素材草稿>" --cues work/cues_en.json --anim shot1_en
python tools/jianying/audit_language.py --draft "<英文草稿>"
```

判据顺序：盘点表没有无法解释的 `none` → 英文总长 ≤ 中文段长 → 最长字幕 ≤ 65 字符 → 片长等于母版 → 审计 PASS。

## 出问题先看哪条

| 症状 | 条目 |
|---|---|
| 没声音、波形平线 | DB-33 |
| 字幕抢跑或落后 | DB-36 |
| 字幕文字和念的不是同一句 | DB-37 |
| 全片晚几秒 | DB-38 |
| 成片开头是播放按钮 | DB-31 |
| 文字被画幅裁掉 | DB-42 |
| 构建说 21 秒、视频是 25 秒 | DB-44 |
| 片子比中文版长 | DB-43 |
| 开场句没有动词 | DB-39 |
| 翻译逻辑反了（or / 手动 vs 自动） | DB-40 |

## 不要做

- 不要拿剪辑师唯一的一份草稿直接跑 `relanguage.py`。先复制目录；写回前关剪映，或让剪映停在首页。
- 不要猜路径和文件名。读 `work/inventory.json` 和草稿的素材表。
- 判据红了不要改判据。阈值不对就拿测量数据说话。
- 加依赖要同步改 `requirements.txt` / `package.json`。
- 不要把画面标注和台词字幕混在一起翻。标注跟画面，台词跟语音。

## 收工判据

- `audit_language.py` 输出 `PASS`、退出码 0。
- `audit_media.py` 没有缺路径、没有孤立素材。
- 抽三帧看过：开场、文字最多的一帧、片尾。文字距画幅边 ≥ 40px。
- 交付说明写清：片长、替换段位置、回退点（备份文件名）。
