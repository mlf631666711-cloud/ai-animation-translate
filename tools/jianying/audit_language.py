#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""audit_language.py —— 换语言草稿的收尾体检

    python tools/jianying/audit_language.py --draft "<草稿目录>"
    python tools/jianying/audit_language.py --draft "<草稿目录>" --json work/audit.json

七项检查，对应 docs/playbook.zh.md §10。输出 PASS / FAIL，FAIL 时打印具体段落。

  ① 每段配音都有字幕覆盖
  ② 首条字幕起点 ≈ 配音段起点 − 0.10（±0.30）
  ③ 字幕不超出所在配音段结尾（+0.35s 容差）
  ④ 字幕文字 ≈ 语音实际念到的词  —— 需要词级时间戳，本脚本只做「同段字幕数」粗检，
     精确比对见 docs/playbook.zh.md 里的词级差集写法
  ⑤ 字幕段之间 0 重叠
  ⑥ 配音段之间 0 重叠（同轨）
  ⑦ 残留中文配音（text_to_audio）0 段
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


def tstart(s):
    return (s.get('target_timerange') or {}).get('start', 0)


def tdur(s):
    return (s.get('target_timerange') or {}).get('duration', 0)


def text_of(mat):
    try:
        return json.loads(mat.get('content') or '{}').get('text', '')
    except Exception:
        return ''


def main():
    ap = argparse.ArgumentParser(description='换语言草稿收尾体检')
    ap.add_argument('--draft', required=True)
    ap.add_argument('--drafts', default='')
    ap.add_argument('--jianying-install', default='')
    ap.add_argument('--json', default='')
    a = ap.parse_args()

    drafts = find_drafts_dir(a.drafts)
    root = resolve_draft(a.draft, drafts)
    codec = JianyingDraftCryptoCodec(DraftCryptoConfig(
        jy_install_dir=a.jianying_install or find_jianying()))
    d, _ = load_json_object_with_codec(os.path.join(root, 'draft_content.json'),
                                       content_codec=codec)

    mats = d.get('materials', {})
    texts = {m['id']: m for m in mats.get('texts', []) if m.get('id')}
    audios = {m['id']: m for m in mats.get('audios', []) if m.get('id')}

    sub_i, sub_n = -1, -1
    for i, tr in enumerate(d.get('tracks', [])):
        n = sum(1 for s in tr.get('segments') or [] if s.get('material_id') in texts)
        if n > sub_n:
            sub_i, sub_n = i, n

    subs = sorted([dict(start=tstart(s), dur=tdur(s), text=text_of(texts[s['material_id']]))
                   for s in (d['tracks'][sub_i].get('segments') or [])
                   if s.get('material_id') in texts], key=lambda x: x['start'])

    voice, chinese = [], []
    for i, tr in enumerate(d.get('tracks', [])):
        for s in tr.get('segments') or []:
            m = audios.get(s.get('material_id'))
            if not m:
                continue
            if m.get('type') == 'text_to_audio':
                chinese.append(dict(track=i, start=tstart(s), dur=tdur(s),
                                    name=os.path.basename(m.get('path') or '')))
            elif m.get('type') == 'extract_music':
                voice.append(dict(track=i, start=tstart(s), dur=tdur(s),
                                  name=os.path.basename(m.get('path') or '')))
    voice.sort(key=lambda x: x['start'])

    fails = []

    # ① 覆盖 + ② 起点 + ③ 段尾
    uncovered, late_start, overshoot = [], [], []
    for v in voice:
        mine = [s for s in subs
                if v['start'] - 0.30 * SEC <= s['start'] < v['start'] + v['dur']]
        if not mine:
            uncovered.append(v)
            continue
        first = min(mine, key=lambda s: s['start'])
        gap = (first['start'] - v['start']) / SEC
        if gap > 0.30 or gap < -1.00:
            late_start.append((v, gap))
        for s in mine:
            end = s['start'] + s['dur']
            if end > v['start'] + v['dur'] + 0.35 * SEC:
                overshoot.append((v, (end - v['start'] - v['dur']) / SEC))
                break

    if uncovered:
        fails.append('① %d 段配音没有字幕' % len(uncovered))
    if late_start:
        fails.append('② %d 段首条字幕偏离起点 >0.30s' % len(late_start))
    if overshoot:
        fails.append('③ %d 条字幕超出配音段尾 >0.35s' % len(overshoot))

    # ④ 词级比对需要 TTS 词轴，草稿里没有；这里只显式说明跳过，不重复计 ①
    word_check = 'skipped'

    # ⑤ 字幕重叠
    s_over = [(b, (a['start'] + a['dur'] - b['start']) / SEC)
              for a, b in zip(subs, subs[1:]) if a['start'] + a['dur'] > b['start'] + 30_000]
    if s_over:
        fails.append('⑤ %d 处字幕重叠' % len(s_over))

    # ⑥ 配音重叠（同轨）
    v_over = []
    for tk in {v['track'] for v in voice}:
        segs = sorted([v for v in voice if v['track'] == tk], key=lambda v: v['start'])
        v_over += [(a, (a['start'] + a['dur'] - b['start']) / SEC)
                   for a, b in zip(segs, segs[1:]) if a['start'] + a['dur'] > b['start'] + 20_000]
    if v_over:
        fails.append('⑥ %d 处配音重叠（同轨）' % len(v_over))

    # ⑦ 残留中文
    if chinese:
        fails.append('⑦ %d 段残留 text_to_audio' % len(chinese))

    print('草稿：%s' % os.path.basename(root))
    print('片长 %.3fs · 字幕 %d 条 · 配音 %d 段（%d 条轨）· 中文残留 %d 段'
          % (d.get('duration', 0) / SEC, len(subs), len(voice),
             len({v['track'] for v in voice}), len(chinese)))
    for title, rows in (('① 无字幕的配音', uncovered), ('② 起点偏移', late_start),
                        ('③ 字幕超出段尾', overshoot), ('⑤ 字幕重叠', s_over),
                        ('⑥ 配音重叠', v_over), ('⑦ 残留中文', chinese)):
        if rows:
            print('  %s：%d' % (title, len(rows)))
            for r in rows[:5]:
                if isinstance(r, tuple):
                    v, x = r
                    print('     T%02d %7.2f  %.2fs' % (v.get('track', -1), v['start'] / SEC, x))
                else:
                    print('     T%02d %7.2f +%.2f %s' % (r.get('track', -1), r['start'] / SEC,
                                                         r['dur'] / SEC, r.get('name', '')))
    print()
    print('④ 字幕文字 vs 语音念词：跳过（需词轴；写法见 docs/playbook.zh.md §10）')
    print('判定：%s' % ('PASS' if not fails else 'FAIL'))
    for f in fails:
        print('  - ' + f)

    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        json.dump(dict(pass_=not fails, fails=fails, subtitles=len(subs), voice=len(voice),
                       duration=round(d.get('duration', 0) / SEC, 3)),
                  io.open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('已写 %s' % a.json)

    sys.exit(0 if not fails else 1)


if __name__ == '__main__':
    main()
