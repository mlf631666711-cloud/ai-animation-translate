# 一键流程 · 中文动画出英文版

[中文](pipeline.zh.md) · [English](pipeline.en.md)

一条命令一步，每步都有产物和判据。跑完七步得到一份能直接打开的剪映草稿。

```
环境 → 文案 → 盘点 → 语音 → 字幕 → 换语言 → 体检
```

前五步不碰剪映工程，最后两步才写草稿。**任何一步判据不过，不要进下一步。**

## 0 环境

```bash
python tools/check_env.py          # 缺什么给什么安装命令
```

要 Python ≥ 3.9、Node、Chrome、ffmpeg/ffprobe、剪映（草稿加密依赖它的 `videoeditor.dll`）。

## 1 写分段文案

```json
{ "segments": [
  { "id": "s01", "shot": 1, "text": "Racing fans, look here!" },
  { "id": "s02", "shot": 1, "text": "Two columns, eight levels.", "read": "…喂给 TTS 的替身写法（可选）" }
] }
```

分段口径：句末标点（`. ! ?`）独立成段；逗号、冒号、破折号结尾视为排版换行，与下一行合并。

## 2 盘点中文母版

```bash
python tools/jianying/inventory.py --draft "<中文草稿目录>" --json work/inventory.json
```

输出一条字幕一行：序号 / 时间 / 文本 / 对应配音（轨号 + 时间 + 素材）。看三件事：

- **配音分布在几条轨**。分散在多条轨时，只看段数最多的那条会漏段（实测漏过 10 段，成片一半中文）。
- **哪些字幕没有配音**。这些是画面标注，时间跟画面，不跟语音。
- **同轨重叠**。中文原版允许跨轨交叉，同轨重叠才是问题。

判据：缺配音的行显示 `none`。不认识这些 `none`，就不要开始翻。

## 3 合成语音

```bash
python tools/tts.py --segments work/segments.json --voice en-US-JennyNeural --out work/tts
```

产物：

| 文件 | 用途 |
|---|---|
| `s01.mp3` / `s01.wav` | 48k 单声道，直接进剪映 |
| `s01.words.json` | 词级时间戳，切字幕用 |
| `_durations.json` | 每段真实时长，排轴用 |
| `joined.wav` | 全稿试听 |

判据：`_durations.json` 里的总时长 ≤ 中文母版对应段时长之和。超了先压：裁尾静音 → 缩句间 → 提语速（≤ +15%），别急着改文案。

## 4 切字幕

```bash
python tools/cues_from_words.py --durations work/tts/_durations.json \
    --inventory work/inventory.json --out work/cues_en.json
```

按词轴切，不按字数硬切。规则见 [playbook §5](playbook.zh.md)。产物是绝对时间的 `[{t0,t1,text}]`，直接给下一步。

判据：最长一条 ≤ 65 字符；每条都在句末或逗号处断；条末没有句号。

## 5 换语言

```bash
python tools/jianying/relanguage.py \
  --master "<中文草稿目录>" \
  --name   "<英文草稿名>" \
  --en-draft "<英文素材草稿>" \
  --cues   work/cues_en.json \
  --anim   shot1_en,shot2_en
```

它只动三处：语音轨、字幕轨、语音下的主画面。剪辑点、版式框、标题条、logo、音效、BGM 全部保留。

判据：片长与母版一致（除非明确删段）；每段画面起点与母版同名段相同。

## 6 体检

```bash
python tools/jianying/audit_language.py --draft "<英文草稿名>"
```

七项检查，`判定：PASS` 才算完。FAIL 会打印具体段落（哪一段没字幕、哪条超尾、哪里重叠）。

再加两项人工确认：

- `python tools/jianying/audit_media.py --draft "<英文草稿名>"`：素材路径 / 素材箱 / id 一致性。
- 抽三帧看画面：开场、文字最多的一帧、片尾。文字离画幅边 ≥ 40px。

## 常见返工点

| 症状 | 先查 |
|---|---|
| 播放没声音 | 新音频素材是不是 `extract_music`；路径有没有 `..`；视频段是否 `volume=0` |
| 字幕和语音差半句 | 字幕是不是照抄了中文时间；TTS 缓存是不是复用了旧句 |
| 全片晚几秒 | 每段尾部静音裁了吗；是不是把多条轨当成一条序列排 |
| 画面是封面/带进度条 | 页面有没有裸模式；渲染器的 `--query` 有没有传到主渲染分支 |
| 文字出画 | 坐标是不是按中文字数写死的；换英文后重测过宽度吗 |
