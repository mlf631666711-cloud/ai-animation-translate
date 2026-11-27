#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""cues_from_words.py —— 用词级时间戳把整句切成字幕条

    python tools/cues_from_words.py --durations work/tts/_durations.json \
        --inventory work/inventory.json --out work/cues_en.json

    # 没有盘点表时按顺序排（段间 0.12s）
    python tools/cues_from_words.py --durations work/tts/_durations.json --out work/cues_en.json

输出：`[{ "t0": 12.34, "t1": 14.02, "text": "..." }, ...]`，绝对时间（秒），可直接喂给
`tools/jianying/relanguage.py --cues`。

切分规则（对应 docs/playbook.zh.md §5）：
  · 先按句末标点断；没到上限不硬切
  · 超过 --max-chars 才切，切点回退到最近的词边界，优先逗号/分号处
  · 不在冠词、介词、连词、be 动词后面断
  · 条末不加句号，型号/数字不拆
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys

if (getattr(sys.stdout, 'encoding', '') or '').lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

NO_BREAK_AFTER = {'a', 'an', 'the', 'of', 'to', 'in', 'on', 'at', 'by', 'for', 'with',
                  'and', 'or', 'but', 'is', 'are', 'was', 'were', 'be', 'been',
                  'very', 'more', 'most', 'than', 'that', 'which', 'as'}


def load_words(path):
    if not path or not os.path.isfile(path):
        return []
    return json.load(io.open(path, encoding='utf-8'))


def split_lines(text, max_chars):
    """按词切行。返回 [(line_text, first_word_index)] —— 词索引用来对时间。"""
    tokens = text.split()
    if not tokens:
        return []
    lines, cur, start = [], [], 0
    for i, w in enumerate(tokens):
        cand = (' '.join(cur + [w])).strip()
        if cur and len(cand) > max_chars:
            # 回退：如果当前最后一个词是禁断词，继续带上这个词
            if cur[-1].lower().strip(',.;:') in NO_BREAK_AFTER:
                cur.append(w)
                continue
            lines.append((' '.join(cur), start))
            cur, start = [w], i
        else:
            cur.append(w)
            # 句末标点优先断（一句一条），其次才是逗号/分号
            if re.search(r'[.!?]$', w) and len(cand) >= 12:
                lines.append((' '.join(cur), start))
                cur, start = [], i + 1
            elif len(cand) > max_chars * 0.55 and re.search(r'[,;:]$', w):
                lines.append((' '.join(cur), start))
                cur, start = [], i + 1
    if cur:
        lines.append((' '.join(cur), start))
    # 清理空行
    return [(t, i) for t, i in lines if t.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--durations', required=True)
    ap.add_argument('--inventory', default='', help='tools/jianying/inventory.py --json 的产物')
    ap.add_argument('--out', required=True)
    ap.add_argument('--max-chars', type=int, default=65)
    ap.add_argument('--lead', type=float, default=0.10, help='字幕比语音早出多少秒')
    ap.add_argument('--tail', type=float, default=0.20, help='末词后留多少秒')
    a = ap.parse_args()

    dd = json.load(io.open(a.durations, encoding='utf-8'))
    segs = dd['segments']
    base = os.path.dirname(os.path.abspath(a.durations))

    if a.inventory:
        inv = json.load(io.open(a.inventory, encoding='utf-8'))
        starts = [v['start'] for v in sorted(inv['voice'], key=lambda v: v['start'])]
        if len(starts) != len(segs):
            print('⚠ 盘点表 %d 段配音 vs 文案 %d 段，按前 %d 段对齐'
                  % (len(starts), len(segs), min(len(starts), len(segs))))
    else:
        starts = [round(sum(s['dur'] for s in segs[:i]) + 0.12 * i, 3) for i in range(len(segs))]

    cues = []
    for i, s in enumerate(segs):
        start = starts[i] if i < len(starts) else 0.0
        words = load_words(os.path.join(base, s.get('words') or ''))
        lines = split_lines(s['text'], a.max_chars)
        if not lines:
            continue
        for j, (line, wi) in enumerate(lines):
            if words and wi < len(words):
                t0 = start + words[wi]['s'] - a.lead
            else:
                t0 = start
            if j + 1 < len(lines) and words and lines[j + 1][1] < len(words):
                t1 = start + words[lines[j + 1][1]]['s']
            else:
                t1 = start + s['dur'] + a.tail
            cues.append(dict(t0=round(max(0.0, t0), 3), t1=round(t1, 3),
                             text=line.rstrip('.,;: ')))
        print('  %-5s %d 行  %.2f→%.2f' % (s['id'], len(lines), cues[-len(lines)]['t0'],
                                          cues[-1]['t1'] if cues else 0))

    cues.sort(key=lambda x: x['t0'])
    for x, y in zip(cues, cues[1:]):
        if x['t1'] > y['t0']:
            x['t1'] = round(max(x['t0'] + 0.6, y['t0'] - 0.02), 3)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(cues, io.open(a.out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('→ %s（%d 条，最长 %d 字符）' % (a.out, len(cues), max(len(c['text']) for c in cues)))


if __name__ == '__main__':
    main()
