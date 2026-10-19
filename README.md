# AI Animation Translate · 一键翻译生产线

把**已出片的中文动画**翻成**英文版动画 + 英文语音**，最后直接生成一份**能在剪映里打开的草稿**。
人只做三件事：**上传文案 → 试听语音 → 确认**；其余由脚本完成。

> 演示片（104.2s）：从**克隆仓库**开始 → 上传文案 → TTS 挑音色 → 镜头配方 → 字幕默认值 → 规格锁 →
> **剪映退到首页再复制草稿** → 出草稿。含客户素材，**只随内部版本提供**，不在本仓库。
> 完整操作手册：`docs/操作手册.md`

> 说明：演示片与真实项目的规格锁只随**内部版本**分发（含客户素材），公开仓库不含。
> 文档里的「规格锁 §x.y」「项目记忆」「缺陷库」是我们内部五件套的引用 —— 请按同样结构建你自己的，
> 再把引用换成你的文件名。

---

## 这套东西解决什么问题

| 环节 | 手工做 | 这套流水线 |
|---|---|---|
| 英文配音 | 逐句录/合成、时长对不上 | `tools/tts.py` 逐段合成，产出真实时长表 |
| 换语言后的时间轴 | 全片重新对锚点，容易整条轨错位 | `tools/scan_times.py` 扫 **6 类时刻语法**，先出嫌疑清单 |
| 逐帧出片 | 手动截屏/录屏 | `tools/render_frames.cjs` 逐帧渲染（4K = `--dpr 2`） |
| 剪映草稿 | 剪映里手点，或第三方库写明文（11.6 打不开） | `tools/jianying/*` 克隆母版目录 + 密文写入，**已验证能打开**；剪映停在首页时**不用退出 App** 也能落盘 |

---

## 5 分钟跑通（Windows · 剪映 11.6）

### 0. 环境

```bash
python tools/check_env.py
```

缺什么它会直接给安装命令。要点：**Python ≥ 3.9** · **Node** · **Chrome** · **ffmpeg/ffprobe** · **剪映 11.6**（草稿加密依赖它的 `videoeditor.dll`）。

### 1. 写分段文案

复制 `examples/segments.example.json`，改成你的稿子：

```json
{ "segments": [
  { "id": "s01", "shot": 1, "text": "Racing fans, look here! ..." },
  { "id": "s02", "shot": 2, "text": "The garage uses an Espressif ...", "read": "…喂给 TTS 的替身写法（可选）" }
]}
```

分段口径：**句末标点（. ! ?）独立成段；逗号/冒号/破折号结尾视为排版换行，与下一行合并**。

### 2. 合成语音

```bash
python tools/tts.py --segments my/segments.json --voice en-US-GuyNeural --out work/tts
```

产出 `s01.wav…` + `joined.wav` + `_durations.json`（每段真实时长，后面的时间轴都吃它）。

### 3. 改英文页面（重锚）

把母版页面复制成 `film1_en.html`，只改五类：**文案 / 词轴 / 元素锚点 / 总时长 / 音轨**。
改完先扫一遍：

```bash
python tools/scan_times.py work/film1_en.html --compare 母版/film1.html
```

⚠ 只扫一种写法会漏掉整条轨（真实事故：相机轨用 `{t:…}`，只 grep `seg(t,A,B)` 得 0 命中，
结果整条 10M 距离条出画）。**6 类都要看**：`seg(t,A,B)` / `seg(t,A)` / `{t:A}` / `t0:/t1:` / 裸比较 / `[A,B]` 数对。

### 4. 逐帧渲染 + 出片

```bash
npm i puppeteer-core
node tools/render_frames.cjs --page work/film1_en.html --out work/frames --dur 17.16 --dpr 2
ffmpeg -y -framerate 30 -i work/frames/f%04d.png -i work/tts/s01.wav \
  -c:v libx264 -crf 18 -pix_fmt yuv420p \
  -x264-params colorprim=bt709:transfer=bt709:colormatrix=bt709 \
  -c:a aac -b:a 192k work/shot1_en.mp4
```

- 4K 就靠 `--dpr 2`（页面 1920×1080 → 输出 3840×2160），脚本会打印实际输出尺寸自证。
- 色彩标签必须走 `-x264-params`，`-color_trc` 对 mp4 是**静默 no-op**。

### 5. 生成剪映草稿（关键一步）

> **先由人做一步：在剪映里把中文母版「复制一份」，命名成英文版的名字（例：`立体车库-英文`），
> 然后跟 AI 说：「我已经把中文版复制了一份，命名为了英文版的了，你在英文版这里操作」。**
>
> 为什么必须人来复制：剪映的「复制草稿」会把**素材箱里的版面素材、绑定的附件关系**一起带过去；
> 自己用脚本新建目录做不到这一点。
> **口径（2026-10-19 定）：动复制出来的素材时，不要去动草稿箱里的东西，完整保留。**
> `rebuild_draft.py` 已按这条实现：母版素材箱的条目一条不删，只把本次用到的素材追加进去。


**两种做法，先看你要哪种：**

| | 方式 A · 最小侵入换语言（**推荐**） | 方式 B · 重建时间轴 |
|---|---|---|
| 适用 | 同一支片换语言，**剪辑师已经剪好** | 从零拼一条新片 / 时间轴本来就要重排 |
| 底 | 母版**原时间轴**（26 轨一条不删） | 母版目录骨架 + 你给的新时间线 |
| 改动 | 只换：语音轨 · 语音下的画面 · 字幕轨 | 内容整体替换 |
| 脚本 | `relanguage.py` | `rebuild_draft.py` |
| **老板口径** | ★ **不要动剪辑时间轴上已剪好的** | 不适用 |

---

#### 方式 A：最小侵入（只换语音 / 语音下的画面 / 字幕轨）

```bash
# ① 以母版时间轴为底，只换三样（不碰其他 23 条轨）
python tools/jianying/relanguage.py \
  --master   "<中文母版草稿目录>" \
  --name     "示例项目-英文" \
  --en-draft "<英文素材源草稿目录>" \
  --cues     work/cues_en.json \
  --anim     shot1_en,shot2_en,shot3_en

# ② 交付体检（全绿再换名）
python tools/jianying/audit_media.py --draft "<…>/示例项目-英文.relang"

# ③ 换名 + 写索引（剪映先退到首页）
python tools/jianying/swap_draft.py --name "示例项目-英文"
```

它具体改什么、为什么这么改（**必须守住**）：

| 允许改 | 规则 |
|---|---|
| ① 语音轨 | 整条换成英文 wav，从 0 顺铺，段间 0.12s 呼吸 |
| ② 语音下的画面 | AI 动画段**边界绑语音段**（S01→0~17.17 / S02→17.17~34.22 / S07→86.80~98.25）；中间 B-roll 在剩余区间**等比缩放**，只挪时间不换素材 |
| ③ 字幕轨 | 整条换成英文（白字 #FFFFFF / 黑描边 0.08 / 思源黑体 CN Heavy / 字号 5 / 无句号） |
| **不许** | 重排镜头顺序、删段、动版式框 / 标题条 / 版式文字 / logo / 音效 / BGM |

`cues_en.json` 长这样（`t0/t1` 是秒）：

```json
[{"seg":"S01","t0":0.0,"t1":2.62,"text":"Racing fans, look here"}]
```

> ⚠️ 两个必须知道的坑：
> ① 复制 segment 的依赖要**遍历 materials 全部分类**（`placeholder_infos` / `vocal_separations` /
> `material_colors` / `loudnesses` 也是依赖），只挑 `videos/audios/texts` 会让 `extra_material_refs` 悬空；
> ② 母版的字幕段可能是 `visible:false`（剪辑时关掉的），换成英文字幕后要设可见。

---

#### 方式 B：重建时间轴（从零拼新片时用）

先准备两样：
- `work/draft_content.plain.json`：你的时间线内容（明文 JSON）。**从母版导出再改**：
  `python tools/jianying/dump_live.py --draft "<母版目录>" --out work/draft_content.plain.json`
- 一个**确定能在剪映里打开的**母版草稿目录（比如你原来的中文稿）

```bash
# ① 克隆母版 + 换内容 + 自检（不碰母版）
python tools/jianying/rebuild_draft.py \
  --master "<剪映草稿目录>" \
  --name   "示例项目" \
  --content work/draft_content.plain.json \
  --cover   work/cover.jpg

# ② 换名 + 写索引（剪映先退到首页！）
python tools/jianying/swap_draft.py --name "示例项目"

# ③ 交付体检
python tools/jianying/audit_media.py --draft "<剪映草稿目录>"
```

体检全绿再打开剪映。三处 id 必须一致（内容素材 / meta 条目 / `draft_virtual_store` 树）——
不一致的表现是**素材箱空着**（时间线照样能播，很容易漏）。

---

## 目录

```
tools/
  check_env.py            环境自检（第一条命令）
  tts.py                  分段 TTS + 时长表
  scan_times.py           6 类时刻语法扫描（重锚完备性）
  render_frames.cjs       通用逐帧渲染（4K = --dpr 2）
  jianying/
    relanguage.py         最小侵入：只换语音 / 语音下的画面 / 字幕轨
    rebuild_draft.py      克隆母版 → 换内容 → 自检
    swap_draft.py         换名 + 写明文索引
    audit_media.py        交付体检（路径/素材箱/三处 id）
    dump_live.py          现网草稿摊开看（只读）
    _jc/                  剪映草稿加解密（Apache-2.0，见其中 LICENSE）
docs/
  操作手册.md             端到端八步 + 六道检查点 + 故障对策
  规格锁-示例.md          真实项目的规格锁（数值怎么定）
  剪映草稿-规格与坑.md    ★ 目录构成 / 素材箱 / 4 条铁律
examples/                 分段文案、内容 JSON 的样例
```

---

## 已验证的真实结果（不是跑通 demo，是交付过）

| 项 | 数值 |
|---|---|
| 三镜英文动画 | 17.167s / 18.544s / 12.328s（4K · 30fps · bt709） |
| 英文 TTS | 7 段 · 100.24s · 专名回环 34/34 · 汉字 0 |
| 剪映草稿 | 102.148s · 5 轨 · 38 条字幕 · 素材箱 24 个素材 |
| 内容自检 | 29/29（字号/字体/描边/标点/汉字 0/无断档） |
| 结构自检 | 17/17（project.json / 4 处镜像 md5 / 三处 id / 索引唯一） |

---

## 常见问题

| 现象 | 原因 | 处理 |
|---|---|---|
| 剪映报「草稿内容已损坏」 | 缺 `Timelines/project.json`，或 4 处镜像不一致 | 重跑 `rebuild_draft.py`，别手搓目录 |
| 草稿列表看不到 | 索引没写 / 指向 `.staging` | 跑 `swap_draft.py`；列表不刷新就点进任一旧稿再退出 |
| 换名 `WinError 5` | 剪映停在**编辑页**（目录被占） | 退到首页即可，**不用关软件** |
| **素材箱只有音频 / 全空** | 内容素材缺 `local_material_id`，或 `draft_virtual_store.json` 的树里没挂 | 见 `docs/剪映草稿-规格与坑.md` §3，`rebuild_draft.py` 已内置修复 |
| 打开后素材一片红 | 路径失效 | `audit_media.py` 查缺失 |
| 英文空格消失（`Racingfans,`） | 母版逐字 `inline-block` 吃空格 | 空格换 `U+00A0`，字号在**最终 DOM** 上重解 |
| 响度对不上 | 用 RMS 估 LUFS | 真算 BS.1770（ffmpeg `loudnorm` / `ebur128`） |

---

## 出处与授权

**本仓库基于开源项目 [pyJianYingDraft](https://github.com/aoguai/pyJianYingDraft)（Apache-2.0）二次开发，并对它做了实质性改造。**

| 部分 | 来源 | 是否改动 |
|---|---|---|
| `tools/jianying/_jc/draft_crypto.py` · `draft_codec.py` | 上游原样 | **未改**加解密算法；仅保留调用本机 `videoeditor.dll` 的方式，**不修改该 DLL** |
| 注册与落盘（索引 / 换名 / 句柄重试） | 上游实现 + **我们重写** | **已改**：上游的注册器会把 `root_meta_info.json` 按密文写，剪映读不了；改成明文 + 身份三方对齐 + 删僵尸条目 |
| 素材箱（meta / 树 / 内容三层合并） | **本仓库自研** | 上游无此能力 |
| `rebuild_draft` · `swap_draft` · `audit_media` · `dump_live` | **本仓库自研** | — |
| 语音 / 重锚 / 逐帧渲染（`tts.py` · `scan_times.py` · `render_frames.cjs`） | **本仓库自研** | — |

### ★ 相对上游多出来的能力：剪映**开着**也能操作

上游要求先关掉剪映再动草稿（目录被占用会 `WinError 5`）。我们改成**暂存构建 + 换名 + 句柄检测重试**：

1. 先在同级目录把整份新草稿构建成 `<名字>.staging`（不碰剪映正在用的目录）；
2. 落盘时检测目标目录是否被占用，被占用就按 `--retry-free <秒>` 轮询等句柄释放；
3. 句柄一释放，`shutil.move` 换名 + 修明文索引，一次完成。

实测结论：**剪映停在「首页」时目录不带独占句柄，直接换名就行**；只有停在编辑页才会占用。
所以人要做的事只有一件 —— **退到首页（不用退出 App），别把草稿开着**。

> 详细改动清单与代码位置：`docs/对上游的修改.md`

### 授权与边界

- 上游部分遵循 **Apache-2.0**，随附 `LICENSE-apache2.txt`；本仓库对其的修改同样按 Apache-2.0 提供。
- 本仓库其余代码与文档：内部交付用。
- 只在**你自己拥有版权**的素材上使用。不要用它绕过任何付费能力。
- 不做账号/水印/会员相关的任何绕过；只操作**本机已有草稿的本地文件**。
