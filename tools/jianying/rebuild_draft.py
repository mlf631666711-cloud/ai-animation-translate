# -*- coding: utf-8 -*-
"""从「一个能打开的母版草稿」克隆出新的剪映草稿（内容换成你的）

    python tools/jianying/rebuild_draft.py \
        --master "<剪映草稿目录>" \
        --name   "示例项目" \
        --content work/draft_content.plain.json \
        --cover   work/cover.jpg

为什么不是"新建一个草稿目录"：
    剪映 11.6 的草稿是**一整个目录**。缺 `Timelines/project.json` 会直接报「草稿内容已损坏」；
    内容还必须 4 处镜像且 md5 一致。手搓骨架必漏件，克隆最稳。

本脚本做的事（全部幂等，可重跑）：
    1 克隆母版目录（排除 .backup / matting / textReading / 根大图 / subdraft）
    2 内容对齐：id=main_timeline_id、new_version/platform 抄母版、素材补 local_material_id
    3 内容加密一次 → 写 4 处镜像；template.json 写明文快照
    4 meta 继承母版，只改身份（名字/路径/draft_id/时长）+ 按内容重建 draft_materials
    5 draft_virtual_store.json 的树重建（素材箱就靠它）
    6 自检：结构 / 镜像 md5 / 三处 id 集合
说明：不写根索引，注册交给 swap_draft.py（换名时一起做）。
"""
import argparse, hashlib, io, json, os, shutil, sys, time, uuid
if (getattr(sys.stdout, 'encoding', '') or '').lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from _jc.draft_codec import JianyingDraftCryptoCodec, load_json_object_with_codec, write_json_object_with_codec  # noqa
from _jc.draft_crypto import DraftCryptoConfig  # noqa

DEFAULT_DRAFTS = [
    os.environ.get('JY_DRAFTS', ''),
    r'D:/剪映下载/JianyingPro Drafts',
    os.path.expanduser('~/AppData/Local/JianyingPro/Drafts'),
]
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
    raise SystemExit('找不到剪映安装目录（videoeditor.dll），用 --jianying-install 指定')

def default_drafts():
    for d in DEFAULT_DRAFTS:
        if os.path.isdir(d):
            return d
    raise SystemExit('找不到剪映草稿目录，用 --draft-dir 指定')

def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()

def base(p):
    return str(p or '').replace('\\', '/').split('/')[-1]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--master', required=True, help='一个确定能打开的草稿目录')
    ap.add_argument('--name', required=True, help='新草稿名（= 目录名 = 剪映里显示的名字）')
    ap.add_argument('--content', required=True, help='你的 draft_content 明文 JSON')
    ap.add_argument('--cover', default='', help='封面 jpg（不填就沿用母版封面）')
    ap.add_argument('--draft-dir', default='')
    ap.add_argument('--jianying-install', default='')
    ap.add_argument('--draft-id', default='', help='留空则自动生成')
    a = ap.parse_args()

    DRAFTS = a.draft_dir or default_drafts()
    JY = a.jianying_install or find_jianying()
    TGT = os.path.join(DRAFTS, a.name)
    WORK = TGT + '.build'
    codec = JianyingDraftCryptoCodec(DraftCryptoConfig(jy_install_dir=JY))
    print('剪映   %s\n草稿夹 %s\n目标   %s' % (JY, DRAFTS, TGT))

    # ---------- 1 克隆 ----------
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    ignore = shutil.ignore_patterns('.backup', 'matting', 'textReading', '*.png', 'subdraft')
    shutil.copytree(a.master, WORK, ignore=ignore)
    print('① 克隆母版 → %s' % WORK)

    proj = json.load(open(os.path.join(WORK, 'Timelines', 'project.json'), encoding='utf-8'))
    UUID = proj['main_timeline_id']
    master_content, _ = load_json_object_with_codec(os.path.join(a.master, 'draft_content.json'), content_codec=codec)
    master_meta, _ = load_json_object_with_codec(os.path.join(a.master, 'draft_meta_info.json'), content_codec=codec)

    content = json.load(open(a.content, encoding='utf-8'))
    content['id'] = UUID
    content['new_version'] = master_content.get('new_version', content.get('new_version'))
    content['version'] = master_content.get('version', content.get('version'))
    content['platform'] = master_content.get('platform') or content.get('platform') or {}
    content['last_modified_platform'] = master_content.get('last_modified_platform') or {}

    # ---------- 2 素材补 id ----------
    added = 0
    for kind in ('videos', 'images', 'audios'):
        for m in content['materials'].get(kind, []):
            if not m.get('local_material_id'):
                m['local_material_id'] = str(uuid.uuid4()); added += 1
            if not m.get('unique_id'):
                m['unique_id'] = uuid.uuid4().hex
    print('② 内容对齐 id=%s · 补素材 id %d 条' % (UUID[:8] + '…', added))

    # ---------- 3 内容 4 处镜像 ----------
    tls = os.path.join(WORK, 'Timelines', UUID)
    mirrors = [os.path.join(WORK, 'draft_content.json'), os.path.join(tls, 'draft_content.json'),
               os.path.join(WORK, 'template-2.tmp'), os.path.join(tls, 'template-2.tmp')]
    write_json_object_with_codec(mirrors[0], content, content_codec=codec)
    for p in mirrors[1:]:
        shutil.copyfile(mirrors[0], p)
    for p in (os.path.join(WORK, 'draft_content.json.bak'), os.path.join(tls, 'draft_content.json.bak')):
        if os.path.exists(p):
            shutil.copyfile(mirrors[0], p)
    json.dump(content, open(os.path.join(tls, 'template.json'), 'w', encoding='utf-8'), ensure_ascii=False)
    print('③ 内容写入 4 处镜像（md5 %s）' % md5(mirrors[0])[:10])

    # ---------- 4 封面 ----------
    if a.cover and os.path.exists(a.cover):
        for p in (os.path.join(WORK, 'draft_cover.jpg'), os.path.join(tls, 'draft_cover.jpg')):
            shutil.copyfile(a.cover, p)
        print('④ 封面 → %s' % a.cover)

    # ---------- 5 meta ----------
    now_s, now_us = int(time.time()), int(time.time() * 1e6)
    meta = json.loads(json.dumps(master_meta, ensure_ascii=False))
    src_f, dst_f = a.master.replace('\\', '/'), TGT.replace('\\', '/')
    src_b, dst_b = a.master.replace('/', '\\'), TGT.replace('/', '\\')

    def rw(o):
        if isinstance(o, dict):
            return {k: rw(v) for k, v in o.items()}
        if isinstance(o, list):
            return [rw(v) for v in o]
        if isinstance(o, str):
            s = o
            for x, y in ((src_f, dst_f), (src_b, dst_b)):
                if x in s:
                    s = s.replace(x, y)
            return s
        return o

    meta = rw(meta)
    meta['draft_name'] = a.name
    meta['draft_fold_path'] = dst_f
    meta['draft_root_path'] = DRAFTS.replace('\\', '/')
    meta['draft_id'] = a.draft_id or str(uuid.uuid4())
    meta['tm_duration'] = content['duration']
    meta['tm_draft_modified'] = now_us
    meta['tm_draft_create'] = now_us

    def entry(m, metetype, typ):
        d = int(m.get('duration') or 0)
        return {'ai_group_type': '', 'create_time': now_s, 'duration': d, 'enter_from': 0,
                'extra_info': base(m.get('path')), 'file_Path': str(m.get('path') or '').replace('\\', '/'),
                'height': int(m.get('height') or 0), 'id': m['local_material_id'],
                'import_time': now_s, 'import_time_ms': now_us, 'item_source': 1,
                'material_color_tag': '', 'md5': '', 'metetype': metetype,
                'roughcut_time_range': {'duration': d, 'start': 0},
                'sub_time_range': {'duration': -1, 'start': -1},
                'type': typ, 'width': int(m.get('width') or 0)}

    vids = [m for m in content['materials'].get('videos', []) if m.get('type') != 'photo']
    pics = [m for m in content['materials'].get('videos', []) if m.get('type') == 'photo'] + \
           list(content['materials'].get('images', []))
    auds = content['materials'].get('audios', [])
    entries = [entry(m, 'video', 0) for m in vids] + [entry(m, 'music', 0) for m in auds] + \
              [entry(m, 'photo', 6) for m in pics]
    groups = {g['type']: g for g in meta.get('draft_materials', [])}
    for t in (1, 2, 3, 7, 8):
        groups[t] = {'type': t, 'value': []}   # 母版的音乐/字幕素材别带过来
    groups[0] = {'type': 0, 'value': [e for e in entries if e['type'] == 0]}
    groups[6] = {'type': 6, 'value': [e for e in entries if e['type'] == 6]}
    meta['draft_materials'] = [groups[t] for t in (0, 1, 2, 3, 6, 7, 8)]
    write_json_object_with_codec(os.path.join(WORK, 'draft_meta_info.json'), meta, content_codec=codec)
    print('⑤ meta：视频 %d · 音频 %d · 图片 %d' % (len(vids), len(auds), len(pics)))

    # ---------- 6 素材箱树 ----------
    sp = os.path.join(WORK, 'draft_virtual_store.json')
    store = json.load(open(sp, encoding='utf-8')) if os.path.exists(sp) else {}
    st = store.get('draft_virtual_store')
    if not isinstance(st, list) or len(st) < 2:
        st = [{'type': 0, 'value': [{'creation_time': 0, 'display_name': '', 'filter_type': 0, 'id': '',
                                     'import_time': 0, 'import_time_us': 0, 'material_color_tag': '',
                                     'sort_sub_type': 0, 'sort_type': 0, 'subdraft_filter_type': 0}]},
              {'type': 1, 'value': []},
              {'type': 2, 'value': []}]
    by = {g['type']: g for g in st}
    by.setdefault(1, {'type': 1, 'value': []})['value'] = [{'child_id': e['id'], 'parent_id': ''} for e in entries]
    store['draft_virtual_store'] = [by[t] for t in sorted(by)]
    store['draft_materials'] = [{'type': g['type'], 'value': g['value']} for g in meta['draft_materials'] if g['value']]
    json.dump(store, open(sp, 'w', encoding='utf-8'), ensure_ascii=False)
    print('⑥ 素材箱树：%d 个子项' % len(entries))

    # ---------- 7 自检 ----------
    print('\n=== 自检 ===')
    fails = []
    def ck(cond, label, extra=''):
        print(('  ✅ ' if cond else '  ❌ ') + label + ('  %s' % extra if extra != '' else ''))
        if not cond:
            fails.append(label)

    ck(os.path.exists(os.path.join(WORK, 'Timelines', 'project.json')), 'project.json 存在')
    ck(len({md5(p) for p in mirrors}) == 1, '4 处镜像 md5 一致', md5(mirrors[0])[:10])
    back, _ = load_json_object_with_codec(mirrors[1], content_codec=codec)
    ck(back.get('id') == UUID, '内容 id == main_timeline_id')
    mb, _ = load_json_object_with_codec(os.path.join(WORK, 'draft_meta_info.json'), content_codec=codec)
    ck(mb['draft_id'] == meta['draft_id'] and mb['draft_name'] == a.name, 'meta 身份正确')
    ids_content = {m['local_material_id'] for k in ('videos', 'audios', 'images') for m in back['materials'].get(k, [])}
    ids_meta = {it['id'] for g in mb['draft_materials'] for it in g['value']}
    ids_store = {c['child_id'] for c in store['draft_virtual_store'][1]['value']}
    ck(ids_content == ids_meta == ids_store, '内容 / meta / 素材箱 三处 id 一致', '%d 条' % len(ids_content))
    ck(abs(back['duration'] / 1e6 - content['duration'] / 1e6) < 0.001, '内容时长 %.3fs' % (back['duration'] / 1e6))

    print('\n%s' % ('可以换名了：python tools/jianying/swap_draft.py --name "%s"' % a.name if not fails
                    else '有 %d 项失败，先别换名' % len(fails)))
    return 1 if fails else 0

if __name__ == '__main__':
    sys.exit(main())
