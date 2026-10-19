# -*- coding: utf-8 -*-
"""交付前体检：素材路径 / 素材箱 / 三处 id / 轨道概况

    python tools/jianying/audit_media.py --draft "<剪映草稿目录>"

查的正是"打开才发现"的那几类问题：
  · 素材路径失效（打开一片红）
  · 素材箱空着（时间线能播，左边却没有素材）—— 真源是 draft_virtual_store.json 的树
  · 内容 / meta / 树 三处 id 不一致
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
    ap.add_argument('--jianying-install', default='')
    a = ap.parse_args()
    codec = JianyingDraftCryptoCodec(DraftCryptoConfig(jy_install_dir=a.jianying_install or find_jianying()))

    c, _ = load_json_object_with_codec(os.path.join(a.draft, 'draft_content.json'), content_codec=codec)
    m, _ = load_json_object_with_codec(os.path.join(a.draft, 'draft_meta_info.json'), content_codec=codec)
    sp = os.path.join(a.draft, 'draft_virtual_store.json')
    store = json.load(open(sp, encoding='utf-8')) if os.path.exists(sp) else {}

    print('=== %s ===' % os.path.basename(os.path.normpath(a.draft)))
    print('时长 %.3fs · 帧率 %s · 轨道 %d' % (c['duration'] / 1e6, c.get('fps'), len(c['tracks'])))
    for i, t in enumerate(c['tracks']):
        print('  轨%d %-6s %d 段' % (i, t['type'], len(t['segments'])))

    # 1 路径
    miss, total, no_lm = [], 0, 0
    for kind in ('videos', 'audios', 'images'):
        for x in c['materials'].get(kind, []):
            p = str(x.get('path') or '')
            if not p:
                continue
            total += 1
            if not x.get('local_material_id'):
                no_lm += 1
            if not os.path.exists(p):
                miss.append(p)
    print('\n素材 %d 条 · 缺文件 %d · 缺 local_material_id %d' % (total, len(miss), no_lm))
    for p in miss[:8]:
        print('   ❌ ' + p)
    if no_lm:
        print('   → 缺 id 会导致「素材箱里一个都没有」，见 docs/剪映草稿-规格与坑.md §3')

    # 2 三处 id
    ids_c = {x['local_material_id'] for k in ('videos', 'audios', 'images')
             for x in c['materials'].get(k, []) if x.get('local_material_id')}
    ids_m = {it['id'] for g in m.get('draft_materials', []) for it in (g.get('value') or [])}
    tree = next((g for g in (store.get('draft_virtual_store') or []) if g.get('type') == 1), None)
    ids_s = {i['child_id'] for i in ((tree or {}).get('value') or [])}
    print('\n三处 id：内容 %d · meta %d · 素材箱树 %d' % (len(ids_c), len(ids_m), len(ids_s)))
    ok = ids_c == ids_m == ids_s
    print('   一致：%s' % ('✅' if ok else '❌（素材箱会缺东西）'))

    ok_all = ok and not miss and no_lm == 0
    print('\n结论：%s' % ('可以交付 ✅' if ok_all else '先修上面标 ❌ 的项'))
    return 0 if ok_all else 1

if __name__ == '__main__':
    sys.exit(main())
