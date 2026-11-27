#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""inventory.py —— 翻译前盘点：把字幕、配音、轨号摊成一张表

    python tools/jianying/inventory.py --draft "<草稿目录>"
    python tools/jianying/inventory.py --draft "<草稿目录>" --json work/inventory.json

为什么需要它：配音可能分散在多条音频轨上。只看段数最多的那条，会漏掉整段配音，
成片一半中文一半英文，而所有时间轴判据都是绿的。

输出三块：
  ① 每条字幕一行：序号 / 时间 / 文本 / 最近的配音段（轨号 + 时间 + 素材名）
  ② 段数汇总：字幕 N 条、配音 M 段、分布在 K 条轨
  ③ 异常：没有配音的字幕、没有字幕的配音、跨轨重叠

判据：缺配音的配音行显式标 `none`。这张表没打印出来，不要开始翻译。
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys

if (getattr(sys.stdout, 'encoding', '') or '').lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '_jc'))

from _jc.draft_codec import JianyingDraftCryptoCodec, load_json_object_with_codec  # noqa: E402
from _jc.draft_crypto import DraftCryptoConfig  # noqa: E402

DEFAULT_DRAFTS = [os.environ.get('JY_DRAFTS', ''),
                  os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'JianyingPro', 'Drafts')]
JY_ROOTS = [os.environ.get('JY_HOME', ''), r'C:/Program Files/JianyingPro']

SEC = 1_000_000


def find_drafts_dir(explicit: str) -> str:
    if explicit:
        return explicit
    for d in DEFAULT_DRAFTS:
        if os.path.isdir(d):
            return d
    raise SystemExit('找不到剪映草稿目录，用 --drafts 指定')


def find_jianying() -> str:
    for root in JY_ROOTS:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root), reverse=True):
            d = os.path.join(root, name)
            if os.path.isdir(d) and os.path.exists(os.path.join(d, 'videoeditor.dll')):
                return d
    raise SystemExit('找不到剪映安装目录，用 --jianying-install 指定')


def resolve_draft(arg: str, drafts: str) -> str:
    if os.path.isdir(arg):
        return arg
    cand = os.path.join(drafts, arg)
    if os.path.isdir(cand):
        return cand
    raise SystemExit('找不到草稿：%s' % arg)


def tstart(seg):
    return (seg.get('target_timerange') or {}).get('start', 0)


def tdur(seg):
    return (seg.get('target_timerange') or {}).get('duration', 0)


def text_of(mat):
    try:
        return json.loads(mat.get('content') or '{}').get('text', '')
    except Exception:
        return ''


def main():
    ap = argparse.ArgumentParser(description='翻译前盘点：字幕 / 配音 / 轨号')
    ap.add_argument('--draft', required=True, help='草稿目录，或 <drafts> 下的草稿名')
    ap.add_argument('--drafts', default='', help='剪映草稿根目录')
    ap.add_argument('--jianying-install', default='')
    ap.add_argument('--max-gap', type=float, default=4.0,
                    help='字幕与配音起点相差超过这个秒数就算「无配音」（默认 4s）')
    ap.add_argument('--json', default='', help='把盘点结果写成 JSON')
    a = ap.parse_args()

    drafts = find_drafts_dir(a.drafts)
    root = resolve_draft(a.draft, drafts)
    codec = JianyingDraftCryptoCodec(DraftCryptoConfig(
        jy_install_dir=a.jianying_install or find_jianying()))
    d, decoded = load_json_object_with_codec(os.path.join(root, 'draft_content.json'),
                                             content_codec=codec)

    mats = d.get('materials', {})
    texts = {m['id']: m for m in mats.get('texts', []) if m.get('id')}
    audios = {m['id']: m for m in mats.get('audios', []) if m.get('id')}
    videos = {m['id']: m for m in mats.get('videos', []) if m.get('id')}

    # ① 字幕轨：段数最多的「文本素材」轨。不要按 track.type 判 —— 老草稿全是 mixed。
    sub_i, sub_n = -1, -1
    for i, tr in enumerate(d.get('tracks', [])):
        n = sum(1 for s in tr.get('segments') or [] if s.get('material_id') in texts)
        if n > sub_n:
            sub_i, sub_n = i, n

    # ② 配音：所有含音频素材的段，按轨分组
    voice = []
    by_track = {}
    for i, tr in enumerate(d.get('tracks', [])):
        for s in tr.get('segments') or []:
            mid = s.get('material_id')
            if mid in audios:
                mat = audios[mid]
                typ = mat.get('type')
                kind = 'voice' if typ in ('text_to_audio', 'extract_music') else (
                    'bgm' if typ == 'music' else 'sfx')
                voice.append(dict(track=i, start=tstart(s), dur=tdur(s), mat=mat, kind=kind))
                by_track[i] = by_track.get(i, 0) + 1

    subs = []
    if sub_i >= 0:
        for s in d['tracks'][sub_i].get('segments') or []:
            mid = s.get('material_id')
            if mid in texts:
                subs.append(dict(track=sub_i, start=tstart(s), dur=tdur(s),
                                 text=text_of(texts[mid])))
    subs.sort(key=lambda x: x['start'])
    voice.sort(key=lambda x: x['start'])

    print('草稿：%s' % os.path.basename(root))
    print('片长 %.3fs · %d 轨 · 字幕轨 T%02d（%d 条）· 音频轨 %d 条（%d 段）%s'
          % (d.get('duration', 0) / SEC, len(d.get('tracks', [])), sub_i, len(subs),
             len(by_track), len(voice), '' if decoded else ' [明文]'))
    kinds = {}
    for v in voice:
        kinds.setdefault(v['track'], {}).setdefault(v['kind'], 0)
        kinds[v['track']][v['kind']] += 1
    print('音频分布：' + '  '.join(
        'T%02d:%d(%s)' % (k, by_track[k], '/'.join(sorted(kinds[k]))) for k in sorted(by_track)))
    voice_tracks = {v['track'] for v in voice if v['kind'] == 'voice'}
    print('配音轨：%s（其余为音效/BGM，不参与字幕配位）'
          % (', '.join('T%02d' % t for t in sorted(voice_tracks)) or '未识别'))
    print()
    print('%3s  %8s  %5s  %-46s  %s' % ('#', '时间', '时长', '字幕', '对应配音（轨/时间/素材）'))

    used = set()
    rows = []
    pool = [v for v in voice if v['kind'] == 'voice'] or voice
    for i, s in enumerate(subs, 1):
        # 先判「落在某个配音段内部」（长段覆盖多条字幕），再退到「起点相近」
        cover = [v for v in pool if v['start'] - 0.30 * SEC <= s['start'] < v['start'] + v['dur']]
        cand = cover or [v for v in pool if abs(v['start'] - s['start']) <= a.max_gap * SEC]
        best = min(cand, key=lambda v: abs(v['start'] - s['start'])) if cand else None
        if best and (cover or abs(best['start'] - s['start']) <= a.max_gap * SEC):
            used.add(id(best))
            vtxt = 'T%02d %7.2f %s' % (best['track'], best['start'] / SEC,
                                       os.path.basename(best['mat'].get('path') or
                                                        best['mat'].get('name') or '?'))
        else:
            vtxt = 'none'
        body = s['text'].replace('\n', ' / ')
        if len(body) > 44:
            body = body[:43] + '…'
        print('%3d  %8.2f  %5.2f  %-46s  %s' % (i, s['start'] / SEC, s['dur'] / SEC, body, vtxt))
        rows.append(dict(index=i, start=round(s['start'] / SEC, 3), dur=round(s['dur'] / SEC, 3),
                         text=s['text'], voice=vtxt))

    orphan_v = [v for v in pool if id(v) not in used]
    print()
    n_voice = sum(1 for v in voice if v['kind'] == 'voice')
    print('汇总：字幕 %d 条 · 配音 %d 段 · 分布在 %d 条配音轨（音频段总计 %d）'
          % (len(subs), n_voice, len(voice_tracks), len(voice)))
    print('无配音的字幕：%d 条%s' % (sum(1 for r in rows if r['voice'] == 'none'),
                                '' if not rows else '（多数是画面标注，属正常）'))
    print('没有对应字幕的配音：%d 段' % len(orphan_v))
    for v in orphan_v[:8]:
        print('   T%02d %7.2f +%.2f  %s' % (v['track'], v['start'] / SEC, v['dur'] / SEC,
                                            os.path.basename(v['mat'].get('path') or
                                                             v['mat'].get('name') or '?')))
    # 同轨重叠
    over = 0
    for i in by_track:
        segs = sorted([v for v in voice if v['track'] == i], key=lambda v: v['start'])
        for x, y in zip(segs, segs[1:]):
            if x['start'] + x['dur'] > y['start'] + 20_000:
                over += 1
    print('同轨配音重叠：%d 处' % over)

    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        json.dump(dict(draft=os.path.basename(root), duration=round(d.get('duration', 0) / SEC, 3),
                       subtitle_track=sub_i, rows=rows,
                       voice=[dict(track=v['track'], start=round(v['start'] / SEC, 3),
                                   dur=round(v['dur'] / SEC, 3),
                                   name=os.path.basename(v['mat'].get('path') or '')) for v in voice]),
                  io.open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('已写 %s' % a.json)

    if len(subs) == 0:
        sys.exit('读不到字幕段：换 --draft 或升级草稿版本')


if __name__ == '__main__':
    main()
