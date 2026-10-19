# -*- coding: utf-8 -*-
"""英文文案 → 逐段 TTS（edge-tts）

    python tools/tts.py --segments examples/segments.example.json --voice en-US-GuyNeural --out work/tts

产物：
    work/tts/s01.mp3 / s01.wav …   每段一条（48k 单声道 wav，便于剪映/ffmpeg 直接用）
    work/tts/joined.wav            全稿拼一条（段间静音 0.35s，供试听）
    work/tts/_durations.json       每段真实时长（后续重锚/时间轴都吃这个）

分段口径（不要自己乱分）：
    · 以 . ! ? 结尾 → 独立成段
    · 以 , : — 结尾 → 视为排版性断行，与下一行合并

读音替身：segments.json 里每条可带 "read" 字段（如 "2.4GHz"），只影响喂给 TTS 的字符，
          上屏文案仍然是 "text"。
"""
import argparse, asyncio, io, json, os, subprocess, sys, wave
if (getattr(sys.stdout, 'encoding', '') or '').lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def sh(cmd):
    p = subprocess.run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit('命令失败：%s\n%s' % (' '.join(cmd), (p.stderr or '')[-400:]))
    return p

def dur(p):
    return float(sh(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', p]).stdout.strip())

async def synth(text, voice, rate, mp3):
    import edge_tts
    kw = {'voice': voice, 'text': text}
    if rate:
        kw['rate'] = rate
    await edge_tts.Communicate(**kw).save(mp3)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--segments', required=True)
    ap.add_argument('--voice', default='en-US-GuyNeural')
    ap.add_argument('--rate', default='', help='例如 -4%%（edge-tts 的 rate 写法）')
    ap.add_argument('--out', default='work/tts')
    ap.add_argument('--gap', type=float, default=0.35)
    ap.add_argument('--force', action='store_true', help='已存在也重合成')
    a = ap.parse_args()

    spec = json.load(open(a.segments, encoding='utf-8'))
    segs = spec['segments'] if isinstance(spec, dict) else spec
    os.makedirs(a.out, exist_ok=True)

    metas = []
    for s in segs:
        sid = s['id']
        mp3 = os.path.join(a.out, sid + '.mp3')
        wav = os.path.join(a.out, sid + '.wav')
        text = s.get('read') or s['text']
        if a.force or not os.path.exists(mp3):
            asyncio.run(synth(text, a.voice, a.rate, mp3))
            print('  合成 %-5s %s' % (sid, text[:42]))
        if a.force or not os.path.exists(wav) or os.path.getmtime(wav) < os.path.getmtime(mp3):
            sh(['ffmpeg', '-y', '-hide_banner', '-loglevel', 'error', '-i', mp3,
                '-ar', '48000', '-ac', '1', '-c:a', 'pcm_s16le', wav])
        d = dur(wav)
        metas.append({'id': sid, 'shot': s.get('shot'), 'text': s['text'],
                      'spoken': text, 'wav': os.path.basename(wav), 'dur': round(d, 3)})
        print('  %-5s %6.3fs  %s' % (sid, d, text[:46]))

    # joined：段 + 静音
    SR = 48000
    parts = []
    for i, m in enumerate(metas):
        w = wave.open(os.path.join(a.out, m['wav']), 'rb')
        assert w.getframerate() == SR and w.getnchannels() == 1, '需要 48k 单声道：' + m['wav']
        parts.append(w.readframes(w.getnframes()))
        w.close()
        if i < len(metas) - 1:
            parts.append(b'\x00\x00' * int(a.gap * SR))
    joined = os.path.join(a.out, 'joined.wav')
    with wave.open(joined, 'wb') as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(SR)
        out.writeframes(b''.join(parts))

    total = round(sum(m['dur'] for m in metas) + a.gap * (len(metas) - 1), 3)
    json.dump({'voice': a.voice, 'rate': a.rate, 'gap': a.gap, 'total': total, 'segments': metas},
              open(os.path.join(a.out, '_durations.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('\n合计 %.3fs（%d 段）→ %s' % (total, len(metas), a.out))

if __name__ == '__main__':
    main()
