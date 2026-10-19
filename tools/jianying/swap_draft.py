# -*- coding: utf-8 -*-
"""把 <名字>.build 换成正式草稿，并写根索引（明文）

    python tools/jianying/swap_draft.py --name "示例项目"

前提：**剪映已退到首页或已关闭**（停在编辑页会锁目录，也会 30 秒内 autosave 把你改的覆盖掉）。

做的事：
    1 旧目录整包留底到 _backup/<名字>-<时间戳>
    2 .build → 正式目录（shutil.move，剪映在首页时不锁）
    3 改根索引 root_meta_info.json（明文；先备份）
    4 复检：结构 / 索引唯一 / id 一致
"""
import argparse, io, json, os, shutil, sys, time
if (getattr(sys.stdout, 'encoding', '') or '').lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _jc.draft_codec import JianyingDraftCryptoCodec, load_json_object_with_codec  # noqa
from _jc.draft_crypto import DraftCryptoConfig  # noqa

DRAFRTS = [os.environ.get('JY_DRAFTS', ''),
                     os.path.expanduser('~/AppData/Local/JianyingPro/Drafts'),
                     r'D:/JianyingPro Drafts',
                     r'D:/剪映下载/JianyingPro Drafts']
JY_ROOTS = [os.environ.get('JY_HOME', ''),
            r'C:/Program Files/JianyingPro',
            r'D:/JianyingPro',
            r'D:/剪映下载/JianyingPro']

def find_jianying():
    for root in JY_ROOTS:
        if not os.path.isdir(root):
            continue
        for name in sorted(os.listdir(root), reverse=True):
            d = os.path.join(root, name)
            if os.path.isdir(d) and os.path.exists(os.path.join(d, 'videoeditor.dll')):
                return d
    raise SystemExit('找不到剪映安装目录，用 --jianying-install 指定')

IDX = os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'JianyingPro', 'User Data',
                   'Projects', 'com.lveditor.draft', 'root_meta_info.json')

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--name', required=True)
    ap.add_argument('--draft-dir', default='')
    ap.add_argument('--index', default=IDX)
    ap.add_argument('--build-suffix', default='.build')
    ap.add_argument('--dry', action='store_true')
    ap.add_argument('--jianying-install', default='')
    a = ap.parse_args()

    DRAFTS = a.draft_dir or next((d for d in DRAFRTS if os.path.isdir(d)), '')
    if not DRAFTS:
        raise SystemExit('找不到草稿目录，用 --draft-dir 指定')
    TGT = os.path.join(DRAFTS, a.name)
    WORK = TGT + a.build_suffix
    if not os.path.isdir(WORK):
        raise SystemExit('没有待发布的构建：%s（先跑 rebuild_draft.py）' % WORK)

    ts = time.strftime('%Y%m%d-%H%M%S')
    bk = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '_backup', '%s-%s' % (a.name, ts))
    bk = os.path.abspath(bk)

    if a.dry:
        print('[dry] 将把 %s → %s' % (TGT, bk))
        print('[dry] 将把 %s → %s' % (WORK, TGT))
        return 0

    # 1 留底
    if os.path.exists(TGT):
        os.makedirs(os.path.dirname(bk), exist_ok=True)
        try:
            shutil.move(TGT, bk)
        except Exception as e:
            print('❌ 旧目录被占用：%r\n   → 把剪映退到首页/关闭后重跑' % (e,))
            return 2
        print('① 旧稿留底 → %s' % bk)

    # 2 换名
    shutil.move(WORK, TGT)
    print('② 新稿就位 → %s' % TGT)

    # 3 索引
    if not os.path.exists(a.index):
        print('⚠ 找不到根索引 %s（只换了名字，剪映列表可能不刷新）' % a.index)
        return 0
    shutil.copyfile(a.index, a.index + '.bak-swap-%s' % ts)
    idx = json.load(open(a.index, encoding='utf-8'))
    store = idx.get('all_draft_store') or []
    codec = JianyingDraftCryptoCodec(DraftCryptoConfig(jy_install_dir=a.jianying_install or find_jianying()))
    meta, _ = load_json_object_with_codec(os.path.join(TGT, 'draft_meta_info.json'), content_codec=codec)
    did = meta['draft_id']
    norm = lambda p: str(p or '').replace('\\', '/').rstrip('/')
    kept, hit = [], None
    for e in store:
        p = norm(e.get('draft_fold_path'))
        if p == norm(TGT):
            continue                       # 旧记录，稍后替换
        if p.endswith('.build') or p.endswith('.staging'):
            continue                       # 僵尸
        kept.append(e)
    tpl = next((e for e in store if norm(e.get('draft_fold_path')) == norm(TGT)), None) or \
          next((e for e in store if norm(e.get('draft_name')) == a.name), None) or \
          (store[0] if store else {})
    e = json.loads(json.dumps(tpl, ensure_ascii=False))
    e['draft_name'] = a.name
    e['draft_fold_path'] = TGT.replace('/', '\\')
    e['draft_id'] = did
    e['draft_json_file'] = TGT.replace('/', '\\') + r'\draft_content.json'
    e['draft_cover'] = TGT.replace('/', '\\') + r'\draft_cover.jpg'
    kept.insert(0, e)
    idx['all_draft_store'] = kept
    json.dump(idx, open(a.index, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    print('③ 索引 %d → %d 条（已备份原文件）' % (len(store), len(kept)))

    # 4 复检
    ok = True
    def ck(c, label, extra=''):
        nonlocal ok
        print(('  ✅ ' if c else '  ❌ ') + label + (('  ' + str(extra)) if extra else ''))
        ok = ok and bool(c)
    print('\n=== 复检 ===')
    ck(os.path.exists(os.path.join(TGT, 'Timelines', 'project.json')), '结构：project.json 存在')
    idx2 = json.load(open(a.index, encoding='utf-8'))
    hits = [x for x in idx2['all_draft_store'] if norm(x.get('draft_fold_path')) == norm(TGT)]
    ck(len(hits) == 1, '索引：该路径唯一', len(hits))
    ck(hits and hits[0]['draft_id'] == did, '索引：draft_id 与 meta 一致')
    zombie = [x for x in idx2['all_draft_store'] if norm(x.get('draft_fold_path')).endswith(('.build', '.staging', '.old'))]
    ck(not zombie, '索引：无僵尸条目', len(zombie))
    print('\n%s' % ('可以打开剪映了 ✅' if ok else '有失败项，先别打开'))
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main())
