# AI Animation Translate · 一键翻译生产线

把**已出片的中文动画**翻成**英文版动画 + 英文语音**，最后直接生成一份**能在剪映里打开的草稿**。
人只做三件事：**上传文案 → 试听语音 → 确认**；其余由脚本完成。

> 演示片：`demo/WorkBuddy-三步出片-演示-v2.mp4`（72.9s，含 TTS 挑音色 / 镜头配方 / 字幕默认值 / 规格锁）
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
| 剪映草稿 | 剪映里手点，或第三方库写明文（11.6 打不开） | `tools/jianying/*` 克隆母版目录 + 密文写入，**已验证能打开** |

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
demo/                     演示片
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

- 剪映草稿加解密：`tools/jianying/_jc/` 取自 [pyJianYingDraft](https://github.com/aoguai/pyJianYingDraft)（**Apache-2.0**，随附 `LICENSE-apache2.txt`）。它调用本机剪映的 `videoeditor.dll`，**不修改**该 DLL。
- 本仓库其余代码与文档：内部交付用。

> 只在**你自己拥有版权**的素材上使用。不要用它绕过任何付费能力。
