# -*- coding: utf-8 -*-
"""把现网草稿摊开看：明文 JSON + 轨道/素材摘要（排查用）

    python tools/jianying/dump_live.py --draft "…/示例项目" --out work/live.json

⚠ 只读不写：不动草稿任何文件。
"""
import argparse, io, json, os, sys
if (getattr(sys.stdout, 'encoding', '') or '').lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _jc.draft_codec import JianyingDraftCryptoCodec, load_json_object_with_codec  # noqa
from _jc.draft_crypto import DraftCryptoConfig  # noqa

JY_ROOTS = [os.environ.get('JY_HOME', ''),
            r'C:/Program Files/JianyingPro',
            r'D:/JianyingPro',
            r'D:/剪映下载/JianyingPro']

def find_jianying():
    for root in JY_ROOTS:
        if os.path.isdir(root):
            for name in sorted(os.listdir(root), reverse=True):
                d = os.path.join(root, name)
                if os.path.isdir(d) and os.path.exists(os.path.join(d, 'videoeditor.dll')):
                    return d
    raise SystemExit('找不到剪映安装目录，用 --jianying-install 指定')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--draft', required=True)
    ap.add_argument('--out', default='')
    ap.add_argument('--jianying-install', default='')
    a = ap.parse_args()
    codec = JianyingDraftCryptoCodec(DraftCryptoConfig(jy_install_dir=a.jianying_install or find_jianying()))
    c, used = load_json_object_with_codec(os.path.join(a.draft, 'draft_content.json'), content_codec=codec)
    print('解密=%s · %.3fs · %d 轨 · %d 素材' % (
        used, c['duration'] / 1e6, len(c['tracks']),
        sum(len(c['materials'].get(k, [])) for k in ('videos', 'audios', 'images'))))

    V = {m['id']: m for m in c['materials'].get('videos', [])}
    A = {m['id']: m for m in c['materials'].get('audios', [])}
    T = {m['id']: m for m in c['materials'].get('texts', [])}
    for i, tr in enumerate(c['tracks']):
        segs = tr['segments']
        t0 = min(s['target_timerange'].get('start', 0) for s in segs) / 1e6 if segs else 0
        t1 = max(s['target_timerange'].get('start', 0) + s['target_timerange'].get('duration', 0) for s in segs) / 1e6 if segs else 0
        print('\n[%d] %-6s %d 段  %.3f → %.3f' % (i, tr['type'], len(segs), t0, t1))
        for s in segs[:6]:
            mid = s['material_id']
            st = s['target_timerange'].get('start', 0) / 1e6
            du = s['target_timerange'].get('duration', 0) / 1e6
            if mid in V:
                nm = os.path.basename(str(V[mid].get('path', '')))
            elif mid in A:
                nm = str(A[mid].get('name') or os.path.basename(str(A[mid].get('path', ''))))
            elif mid in T:
                try:
                    nm = json.loads(T[mid].get('content') or '{}').get('text', '')[:30]
                except Exception:
                    nm = '(text)'
            else:
                nm = '(?)'
            print('    %7.3f +%6.3f  %s' % (st, du, nm))
        if len(segs) > 6:
            print('    … 还有 %d 段' % (len(segs) - 6))

    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or '.', exist_ok=True)
        json.dump(c, open(a.out, 'w', encoding='utf-8'), ensure_ascii=False)
        print('\n明文已写 %s' % a.out)

if __name__ == '__main__':
    main()
