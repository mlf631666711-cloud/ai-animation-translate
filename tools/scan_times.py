# -*- coding: utf-8 -*-
"""重锚完备性扫描：把一份 HTML/JS 里所有"时刻"抓出来（6 类语法）

    python tools/scan_times.py 你的页面.html
    python tools/scan_times.py 你的页面.html --compare 母版页面.html

为什么必须扫全 6 类：只 grep 一种写法会漏掉整条轨（真实事故：相机轨用 {t:9.44,...}，
只扫 seg(t,A,B) 得 0 命中，结果 10M 距离条整条出画）。

输出是**嫌疑清单**，不是罪证：与母版同值的项可能是数值巧合，要逐个人眼定位。
"""
import argparse, io, json, re, sys
if (getattr(sys.stdout, 'encoding', '') or '').lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PATTERNS = [
    ('seg(t,A,B)', re.compile(r'seg\(\s*t\s*,\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\)')),
    ('seg(t,A)', re.compile(r'seg\(\s*t\s*,\s*([-\d.]+)\s*\)')),
    ('{t:A}', re.compile(r'\bt\s*:\s*([-\d.]+)')),
    ('t0:/t1:', re.compile(r'\bt[01]\s*:\s*([-\d.]+)')),
    ('裸比较', re.compile(r'\bt\s*(>=|<=|>|<)\s*([-\d.]+)')),
    ('[A,B] 数对', re.compile(r'\[\s*([-\d.]+)\s*,\s*([-\d.]+)\s*\]')),
]

def scan(path):
    src = open(path, encoding='utf-8', errors='replace').read()
    lines = src.splitlines()
    found = []
    for name, rx in PATTERNS:
        for i, line in enumerate(lines, 1):
            for m in rx.finditer(line):
                vals = [float(g) for g in m.groups() if g and re.fullmatch(r'[-\d.]+', g)]
                if not vals:
                    continue
                found.append({'kind': name, 'line': i, 'text': m.group(0)[:40], 'vals': vals})
    return found

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('target')
    ap.add_argument('--compare', default='', help='母版文件：同值时标黄（疑似漏改，也可能是巧合）')
    ap.add_argument('--json', default='', help='把结果写到 json')
    a = ap.parse_args()

    tgt = scan(a.target)
    base_vals = set()
    if a.compare:
        for f in scan(a.compare):
            base_vals.update(f['vals'])

    print('=== %s ===' % a.target)
    print('%-11s %-6s %-46s %s' % ('语法', '行号', '原文', '数值'))
    for f in tgt:
        same = ''
        if base_vals and all(v in base_vals for v in f['vals']):
            same = '  ← 与母版同值（重点看）'
        print('%-11s %-6d %-46s %s%s' % (f['kind'], f['line'], f['text'], f['vals'], same))
    print('\n合计 %d 处' % len(tgt))

    kinds = {}
    for f in tgt:
        kinds[f['kind']] = kinds.get(f['kind'], 0) + 1
    print('分布：' + ' · '.join('%s %d' % (k, v) for k, v in kinds.items()))
    print('\n提醒：这份是"嫌疑清单"。改完重锚后逐条人眼确认它属于哪一句、干什么用；')
    print('      与母版同值的项有可能是巧合（不同段复用了同一个数）。')

    if a.json:
        json.dump(tgt, open(a.json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
        print('已写 %s' % a.json)

if __name__ == '__main__':
    main()
