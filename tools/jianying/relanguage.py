# -*- coding: utf-8 -*-
"""relanguage.py —— 最小侵入「换语言」：以母版已剪好的时间轴为底，只换三样

与 rebuild_draft.py 的区别：
  · rebuild_draft：以母版目录为**骨架**，内容按你给的新时间线**重建**（适合从零做一条新片）
  · relanguage  ：以母版时间轴为**底**，只替换语音 / 该语音下的画面 / 字幕轨，**其余轨一字不动**
    ⇒ 剪辑师已经剪好的剪辑点、版式框、标题条、logo、音效、BGM 全部保留

只改三处：
  ① 语音轨：识别含 `text_to_audio` 最多的那条 → 换成 `--voice-dir` 里的 wav（按文件名排序）
  ② 字幕轨：识别 `type=subtitle` 最多的那条 → 换成 `--cues` 里的字幕（复用英文稿的字幕样式）
  ③ 主画面轨：把 AI 动画段（素材名以 `video*` 开头）换成 `--anim` 指定的素材，边界**绑语音段**；
     中间的 B-roll 段在剩余空间里等比缩放（只挪时间，不换素材）

用法：
  python tools/jianying/relanguage.py \
      --master "D:/JianyingPro Drafts/我的片-中文" \
      --name   "我的片-英文" \
      --en-draft "D:/JianyingPro Drafts/我的片-英文-src" \
      --cues  work/cues_en.json \
      --anim  shot1_en,shot2_en,shot3_en
"""
from __future__ import annotations

import argparse
import io
import json
import os
import shutil
import sys
import uuid

if (getattr(sys.stdout, 'encoding', '') or '').lower() not in ('utf-8', 'utf8'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _jc.draft_codec import (JianyingDraftCryptoCodec, load_json_object_with_codec,
                             write_json_object_with_codec)
from _jc.draft_crypto import DraftCryptoConfig

DEFAULT_DRAFTS = [r'D:/剪映下载/JianyingPro Drafts',
                  os.path.join(os.path.expanduser('~'), 'AppData', 'Local', 'JianyingPro', 'Drafts')]
JY_ROOTS = [r'D:/剪映下载/JianyingPro', r'C:/Program Files/JianyingPro']


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


def us(x: float) -> int:
    return int(round(x * 1e6))


def newid() -> str:
    return str(uuid.uuid4()).upper()


def tstart(seg) -> int:
    return (seg.get('target_timerange') or {}).get('start', 0)


def tdur(seg) -> int:
    return (seg.get('target_timerange') or {}).get('duration', 0)


def main() -> None:
    ap = argparse.ArgumentParser(description='最小侵入换语言：只换语音 / 语音下的画面 / 字幕轨')
    ap.add_argument('--master', required=True, help='中文母版草稿目录（时间轴底）')
    ap.add_argument('--name', required=True, help='英文版草稿名（输出到 <drafts>/<name>.relang）')
    ap.add_argument('--en-draft', required=True, help='英文素材源草稿目录（取动画 / 语音 / 字幕样式）')
    ap.add_argument('--cues', required=True, help='英文字幕 JSON：[{t0,t1,text}, ...]')
    ap.add_argument('--anim', default='shot1,shot2,shot3', help='英文动画素材名前缀，逗号分隔、按顺序')
    ap.add_argument('--drafts', default='', help='剪映草稿根目录')
    ap.add_argument('--jianying-install', default='')
    ap.add_argument('--voice-gap', type=float, default=0.12, help='语音段之间的呼吸（秒）')
    a = ap.parse_args()

    drafts = find_drafts_dir(a.drafts)
    codec = JianyingDraftCryptoCodec(DraftCryptoConfig(
        jy_install_dir=a.jianying_install or find_jianying()))
    M = a.master
    E = a.en_draft
    W = os.path.join(drafts, a.name + '.relang')

    # 0 克隆母版目录
    if os.path.isdir(W):
        shutil.rmtree(W)
    shutil.copytree(M, W, ignore=shutil.ignore_patterns(
        '.backup', 'matting', 'textReading', 'adjust_mask', 'Resources', 'deepagent'))
    print('① 克隆母版目录 → %s' % os.path.basename(W))

    proj = json.load(open(os.path.join(W, 'Timelines', 'project.json'), encoding='utf-8'))
    TLID = proj['main_timeline_id']
    CP = os.path.join(W, 'draft_content.json')
    mc, _ = load_json_object_with_codec(CP, content_codec=codec)
    ec, _ = load_json_object_with_codec(os.path.join(E, 'draft_content.json'), content_codec=codec)
    print('② 母版 %.3fs / %d 轨　素材源 %.3fs / %d 轨'
          % (mc['duration'] / 1e6, len(mc['tracks']), ec['duration'] / 1e6, len(ec['tracks'])))

    # 1 定位三条轨
    t2a = {x['id'] for x in mc['materials']['audios'] if x.get('type') == 'text_to_audio'}
    voice_i = max(range(len(mc['tracks'])),
                  key=lambda i: sum(1 for s in mc['tracks'][i]['segments'] if s.get('material_id') in t2a))
    sub_ids = {x['id'] for x in mc['materials']['texts'] if x.get('type') == 'subtitle'}
    sub_i = max(range(len(mc['tracks'])),
                key=lambda i: sum(1 for s in mc['tracks'][i]['segments'] if s.get('material_id') in sub_ids))
    vids = {x['id'] for x in mc['materials']['videos']}
    pic_i = max((i for i in range(len(mc['tracks']))
                 if min((tstart(s) for s in mc['tracks'][i]['segments']), default=9e9) < us(1)),
                key=lambda i: sum(1 for s in mc['tracks'][i]['segments'] if s.get('material_id') in vids))
    print('   语音轨=%d（%d 段）　字幕轨=%d（%d 段）　主画面轨=%d（%d 段）'
          % (voice_i, len(mc['tracks'][voice_i]['segments']),
             sub_i, len(mc['tracks'][sub_i]['segments']),
             pic_i, len(mc['tracks'][pic_i]['segments'])))

    # 2 素材索引（遍历全部分类，别只挑 videos/audios/texts）
    mc_mats = mc.setdefault('materials', {})
    index = {}
    for k, v in ec.get('materials', {}).items():
        if not isinstance(v, list):
            continue
        mc_mats.setdefault(k, [])
        for m in v:
            if isinstance(m, dict) and m.get('id'):
                index[m['id']] = (k, m)
    mc_ids = {m['id'] for v in mc_mats.values() if isinstance(v, list)
              for m in v if isinstance(m, dict) and m.get('id')}
    added = [0]

    def pull(seg):
        need = [seg.get('material_id')] + list(seg.get('extra_material_refs') or [])
        guard = 0
        while need and guard < 500:
            guard += 1
            mid = need.pop()
            if not mid or mid in mc_ids or mid not in index:
                continue
            k, m = index[mid]
            mc_mats.setdefault(k, []).append(json.loads(json.dumps(m, ensure_ascii=False)))
            mc_ids.add(mid)
            added[0] += 1
            need.extend(m.get('extra_material_refs') or [])

    # 3 语音轨
    ext = {x['id'] for x in ec['materials']['audios'] if x.get('type') == 'extract_music'}
    seen, en_voice = set(), []
    for t in ec['tracks']:
        for s in t['segments']:
            if s.get('material_id') in ext and s['material_id'] not in seen:
                seen.add(s['material_id'])
                en_voice.append(s)
    en_voice.sort(key=tstart)
    print('③ 英文语音 %d 段' % len(en_voice))
    cursor, new_voice, bounds = 0.0, [], []
    for k, s in enumerate(en_voice):
        pull(s)
        d = tdur(s)
        seg = json.loads(json.dumps(s, ensure_ascii=False))
        seg['id'] = newid()
        seg['target_timerange'] = {'start': us(cursor), 'duration': d}
        seg['source_timerange'] = {'start': 0, 'duration': d}
        seg.pop('render_timerange', None)
        new_voice.append(seg)
        cursor += d / 1e6
        bounds.append(cursor)
        if k < len(en_voice) - 1:
            cursor += a.voice_gap
    mc['tracks'][voice_i]['segments'] = new_voice
    print('   语音轨 0 → %.3fs（边界 %s）' % (cursor, ['%.2f' % b for b in bounds]))

    # 4 字幕轨
    cues = json.load(open(a.cues, encoding='utf-8'))
    if isinstance(cues, dict):
        cues = cues.get('cues') or cues.get('items') or list(cues.values())[-1]
    cues = sorted(cues, key=lambda c: c['t0'])
    en_sub = sorted((s for t in ec['tracks'] for s in t['segments']
                     if s.get('material_id') in {x['id'] for x in ec['materials']['texts']
                                                 if x.get('type') == 'subtitle'}), key=tstart)
    if len(cues) != len(en_sub):
        raise SystemExit('字幕条数不一致：cues %d / 素材源 %d' % (len(cues), len(en_sub)))
    new_sub = []
    for c, s in zip(cues, en_sub):
        pull(s)
        seg = json.loads(json.dumps(s, ensure_ascii=False))
        seg['id'] = newid()
        seg['target_timerange'] = {'start': us(c['t0']), 'duration': us(c['t1']) - us(c['t0'])}
        seg.pop('source_timerange', None)
        seg.pop('render_timerange', None)
        new_sub.append(seg)
    mc['tracks'][sub_i]['segments'] = new_sub
    print('④ 字幕轨换 %d 条：%.2f → %.2f' % (len(new_sub), cues[0]['t0'], cues[-1]['t1']))

    # 5 主画面轨
    segs = sorted(mc['tracks'][pic_i]['segments'], key=tstart)
    mc['tracks'][pic_i]['segments'] = segs
    vm = {x['id']: x for x in mc['materials']['videos']}
    anim_idx = [k for k, s in enumerate(segs)
                if os.path.basename(str(vm.get(s.get('material_id'), {}).get('path', ''))).startswith('video')]
    print('⑤ 主画面 %d 段，AI 动画 %d 段（下标 %s）' % (len(segs), len(anim_idx), anim_idx))
    names = [x.strip() for x in a.anim.split(',') if x.strip()]
    if len(names) < len(anim_idx):
        raise SystemExit('动画素材不够：需要 %d 个，--anim 给了 %d 个' % (len(anim_idx), len(names)))
    shot = {}
    for x in ec['materials']['videos']:
        b = os.path.basename(str(x.get('path', '')))
        for nm in names:
            if b.startswith(nm):
                shot[nm] = x
    for n, k in enumerate(anim_idx[:len(anim_idx) - 1]):
        a0 = 0.0 if n == 0 else bounds[n - 1]
        b0 = bounds[n]
        m = shot[names[n]]
        if m['id'] not in mc_ids:
            mc_mats.setdefault('videos', []).append(json.loads(json.dumps(m, ensure_ascii=False)))
            mc_ids.add(m['id'])
        segs[k]['material_id'] = m['id']
        segs[k]['target_timerange'] = {'start': us(a0), 'duration': us(b0 - a0)}
        segs[k]['source_timerange'] = {'start': 0, 'duration': min(us(b0 - a0), int(m.get('duration') or us(b0 - a0)))}
        print('   动画%d ← %s  %.2f→%.2f' % (k, os.path.basename(m['path']), a0, b0))

    # 中间 B-roll：原区间 → 新区间等比
    mid = list(range(anim_idx[0] + len(anim_idx) - 1, anim_idx[-1]))
    mid = [k for k in mid if k not in anim_idx]
    if mid:
        b0 = tstart(segs[mid[0]]) / 1e6
        b1 = (tstart(segs[mid[-1]]) + tdur(segs[mid[-1]])) / 1e6
        # 动画分两拨：前面 len-1 段 + 最后 1 段；B-roll 夹在中间
        n0 = bounds[len(anim_idx) - 2]
        n1 = bounds[len(bounds) - 2]
        ratio = (n1 - n0) / (b1 - b0) if b1 > b0 else 1.0
        for k in mid:
            aa, dd = tstart(segs[k]) / 1e6, tdur(segs[k]) / 1e6
            segs[k]['target_timerange'] = {'start': us(n0 + (aa - b0) * ratio), 'duration': us(dd * ratio)}
            sr = segs[k].get('source_timerange')
            if sr:
                sr['duration'] = min(int(sr.get('duration', us(dd))), us(dd * ratio))
        print('   B-roll %d 段：[%.2f,%.2f] → [%.2f,%.2f] ×%.4f' % (len(mid), b0, b1, n0, n1, ratio))

    # 最后一段动画
    k = anim_idx[-1]
    m = shot[names[len(anim_idx) - 1]]
    if m['id'] not in mc_ids:
        mc_mats.setdefault('videos', []).append(json.loads(json.dumps(m, ensure_ascii=False)))
        mc_ids.add(m['id'])
    a0, b0 = bounds[len(bounds) - 2], bounds[len(bounds) - 1]
    segs[k]['material_id'] = m['id']
    segs[k]['target_timerange'] = {'start': us(a0), 'duration': us(b0 - a0)}
    segs[k]['source_timerange'] = {'start': 0, 'duration': min(us(b0 - a0), int(m.get('duration') or us(b0 - a0)))}
    print('   动画%d ← %s  %.2f→%.2f' % (k, os.path.basename(m['path']), a0, b0))

    # 6 时长保持母版
    print('⑥ 时长保持母版 %.3fs' % (mc['duration'] / 1e6))

    # 7 写盘
    targets = [CP, os.path.join(W, 'Timelines', TLID, 'draft_content.json'),
               os.path.join(W, 'template-2.tmp'), os.path.join(W, 'Timelines', TLID, 'template-2.tmp')]
    write_json_object_with_codec(CP, mc, content_codec=codec)
    for p in targets[1:]:
        shutil.copyfile(CP, p)
    json.dump(mc, open(os.path.join(W, 'Timelines', TLID, 'template.json'), 'w', encoding='utf-8'),
              ensure_ascii=False)

    # 8 meta / store：母版为底，只追加本次用到的英文素材
    meta, _ = load_json_object_with_codec(os.path.join(M, 'draft_meta_info.json'), content_codec=codec)
    store = json.load(open(os.path.join(M, 'draft_virtual_store.json'), encoding='utf-8'))
    groups = {g['type']: list(g.get('value') or []) for g in meta['draft_materials']}
    have = {it.get('id') for g in meta['draft_materials'] for it in g['value']}
    kids = list(({g['type']: g for g in store['draft_virtual_store']}.get(1) or {}).get('value') or [])
    seen_kid = {c['child_id'] for c in kids}
    n_new = 0
    for kind, t, mt in (('videos', 0, 'video'), ('audios', 0, 'music')):
        for m in mc_mats.get(kind, []):
            b = os.path.basename(str(m.get('path') or ''))
            if not (any(b.startswith(nm) for nm in names) or (b[:2].upper() == 'S0' and b.endswith('.wav'))):
                continue
            lm = m.get('local_material_id') or m.get('id')
            if not lm or lm in have:
                continue
            groups.setdefault(t, []).append({
                'id': lm, 'create_time': -1, 'import_time': -1,
                'duration': int(m.get('duration') or 0),
                'width': int(m.get('width') or 0), 'height': int(m.get('height') or 0),
                'file_Path': str(m.get('path') or ''), 'metetype': mt,
                'extra_info': b, 'type': 0, 'local_material_id': lm})
            have.add(lm)
            n_new += 1
            if lm not in seen_kid:
                kids.append({'child_id': lm, 'parent_id': ''})
                seen_kid.add(lm)
    meta['draft_materials'] = [{'type': k, 'value': groups[k]} for k in sorted(groups)]
    for g in store['draft_virtual_store']:
        if g['type'] == 1:
            g['value'] = kids
    store['draft_materials'] = [{'type': g['type'], 'value': g['value']} for g in meta['draft_materials']]
    meta['draft_name'] = a.name
    meta['draft_fold_path'] = W.replace('/', '\\')
    meta['tm_duration'] = mc['duration']
    write_json_object_with_codec(os.path.join(W, 'draft_meta_info.json'), meta, content_codec=codec)
    json.dump(store, open(os.path.join(W, 'draft_virtual_store.json'), 'w', encoding='utf-8'),
              ensure_ascii=False)
    print('⑦ 素材箱：新增 %d 条（母版原有 %d 条全部保留）' % (n_new, len(have) - n_new))
    print('\n完成 → %s\n下一步：python tools/jianying/audit_media.py --draft "%s" 全绿后再换成正式名' % (W, W))


if __name__ == '__main__':
    main()
