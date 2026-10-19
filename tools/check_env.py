# -*- coding: utf-8 -*-
"""环境自检：同事拿到仓库后的第一条命令。

    python tools/check_env.py

检查项：Python 版本 / 依赖 / Node / Chrome / ffmpeg / edge-tts 连通性 /
        剪映安装目录（videoeditor.dll）/ 草稿目录。
缺什么直接给安装命令；不改任何文件。
"""
import io, os, shutil, subprocess, sys
if (getattr(sys.stdout, 'encoding', '') or '').lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

OK, BAD, WARN = '✅', '❌', '⚠️ '
rows, bad = [], 0

def ck(cond, name, detail='', fix=''):
    global bad
    tag = OK if cond else BAD
    if not cond:
        bad += 1
    rows.append((tag, name, detail, fix))

def run(cmd, timeout=25):
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, shell=isinstance(cmd, str))
        return p.returncode == 0, (p.stdout or p.stderr or '').strip()
    except Exception as e:
        return False, str(e)

# 1 python
v = sys.version_info
ck(v >= (3, 9), 'Python ≥ 3.9', '当前 %d.%d.%d' % (v[0], v[1], v[2]), 'https://www.python.org/downloads/')

# 2 依赖
for mod, pkg, extra in (('edge_tts', 'edge-tts', ''),
                        ('PIL', 'Pillow', '(可选，画时间线图用)')):
    try:
        __import__(mod)
        ck(True, 'Python 包 %s' % pkg, '已安装')
    except ImportError:
        ck(False, 'Python 包 %s' % pkg, extra or '未安装', 'pip install %s' % pkg)

try:
    import faster_whisper  # noqa
    ck(True, 'Python 包 faster-whisper', '已安装（ASR 回环可用）')
except ImportError:
    ck(True, 'Python 包 faster-whisper', '未安装 —— 仅 ASR 回环会跳过，不影响出片', 'pip install faster-whisper')

# 3 node / chrome / ffmpeg
NODE_FALLBACK = [r'C:/Program Files/nodejs/node.exe', os.path.expanduser('~/AppData/Local/Programs/nodejs/node.exe')]
for exe, name, fix in (('node', 'Node.js', 'https://nodejs.org/'),
                       ('ffmpeg', 'ffmpeg', 'https://ffmpeg.org/download.html 或 winget install Gyan.FFmpeg'),
                       ('ffprobe', 'ffprobe', '随 ffmpeg 一起装')):
    path = shutil.which(exe)
    if not path and exe == 'node':
        path = next((p for p in NODE_FALLBACK if os.path.exists(p)), '')
    flag = '--version' if exe == 'node' else '-version'
    ok, out = run([path or exe, flag])
    ck(ok, name, (out.splitlines()[0][:60] if ok else '未找到') + (('  (' + path + ')') if path and path != exe else ''), fix)

CHROME_CANDIDATES = [
    r'C:/Program Files/Google/Chrome/Application/chrome.exe',
    r'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    os.path.expanduser(r'~/AppData/Local/Google/Chrome/Application/chrome.exe'),
]
chrome = next((p for p in CHROME_CANDIDATES if os.path.exists(p)), '')
ck(bool(chrome), 'Chrome（逐帧渲染用）', chrome or '未找到', '装 Chrome，或在 config.json 里把 chrome 指向你的路径')

# 4 edge-tts 连通性（真的说一句话）
if shutil.which('ffmpeg'):
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), '_tts_probe.mp3')
    try:
        p = subprocess.run([sys.executable, '-m', 'edge_tts', '--voice', 'zh-CN-YunyangNeural',
                            '--text', '测试', '--write-media', tmp], capture_output=True, text=True, timeout=45)
        ok = p.returncode == 0 and os.path.exists(tmp) and os.path.getsize(tmp) > 1000
        ck(ok, 'edge-tts 联网合成', 'ok' if ok else (p.stderr or '')[-120:], '检查网络 / 代理；国内可换 --proxy')
        if os.path.exists(tmp):
            os.remove(tmp)
    except Exception as e:
        ck(False, 'edge-tts 联网合成', str(e)[:100], '检查网络')

# 5 剪映
jy = ''
for root in (os.environ.get('JY_HOME', ''), r'C:/Program Files/JianyingPro', r'D:/JianyingPro', r'D:/剪映下载/JianyingPro', os.path.expanduser('~/AppData/Local/JianyingPro')):
    if not os.path.isdir(root):
        continue
    for name in sorted(os.listdir(root), reverse=True):
        d = os.path.join(root, name)
        if os.path.isdir(d) and os.path.exists(os.path.join(d, 'videoeditor.dll')):
            jy = d
            break
    if jy:
        break
ck(bool(jy), '剪映安装目录（videoeditor.dll）', jy or '未找到', '在 config.json 的 jianying_install 填你的版本目录')

drafts = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'JianyingPro', 'User Data')
ck(os.path.isdir(drafts), '剪映用户数据目录', drafts, '先打开一次剪映让它生成')

# 6 报告
w = max(len(r[1]) for r in rows) + 2
print('\n=== 环境自检 ===')
for tag, name, detail, fix in rows:
    print('%s %s %s' % (tag, name.ljust(w), detail))
    if tag == BAD and fix:
        print('   → ' + fix)
print('\n%s' % ('全部就绪，可以开工 ✅' if bad == 0 else '有 %d 项要修（见上面 → 后面的命令）' % bad))
sys.exit(0 if bad == 0 else 1)
