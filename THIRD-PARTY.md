# 第三方组件

| 组件 | 位置 | 许可 | 我们做了什么 |
|---|---|---|---|
| `jy-draftc` | `tools/jianying/_jc/` | Apache-2.0 | 移植为 Python，`DraftCrypto` 的低层调用改为在子进程里执行，避免 ABI 不一致时崩掉主进程 |

`tools/jianying/_jc/LICENSE-apache2.txt` 是该许可的副本。

## 修改声明（Apache-2.0 §4(b)）

- 原实现为 TypeScript（Node）。本仓库按同样的算法用 Python 重写，接口、函数名与错误类型保持对应。
- `JianyingDraftCrypto` 通过 `ctypes` 直接调用剪映的 `videoeditor.dll`；默认把这次调用放到独立的
  Python 子进程里跑，主进程只接收结果。
- 未修改上游的许可与版权声明。

## 使用到的外部程序

流程调用以下程序，但不随仓库分发，也不在本仓库许可范围内：

- **剪映 / JianyingPro**：草稿加密依赖其 `videoeditor.dll`。
- **ffmpeg / ffprobe**：音频转换与时长读取。
- **Chrome**：逐帧渲染（经 `puppeteer-core`）。
- **edge-tts**：语音合成，走微软在线服务，需联网。
