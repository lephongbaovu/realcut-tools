#!/usr/bin/env python3
"""beatsnap — dời điểm cắt B-roll (và chuyển cảnh trùng điểm cắt) về phách nhạc gần nhất (anh Vũ duyệt 22/11/2026).
python3 beatsnap.py DA [--max 0.15] [--lock 59.56,...] [--dry]
Ưu tiên phách chính (beat) trong ±max, không được thì nửa phách; mốc lock giữ nguyên. Chữ (ads.json keywords) giữ theo lời.
Ghi edit.json/ads.json mới, bản cũ lưu *_prebeat.json."""
import argparse, json, os, shutil, subprocess, sys
import numpy as np
from scipy.signal import stft
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import load_json, probe

DEFAULT_MUSIC = os.path.join(os.path.expanduser('~'), '.realcut', 'music', 'mixkit_837_life_is_a_dream.mp3')

def beat_grid(path):
    sr = 22050; hop = 220
    b = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(sr), '-f', 's16le', '-'], capture_output=True).stdout
    a = np.frombuffer(b, np.int16).astype(np.float32) / 32768
    f, t, Z = stft(a, sr, nperseg=1024, noverlap=1024 - hop); P = np.log1p(10 * np.abs(Z))
    fl = np.maximum(np.diff(P, axis=1), 0).sum(0); fps = sr / hop
    fl = fl - np.convolve(fl, np.ones(30) / 30, 'same'); fl[fl < 0] = 0
    ac = np.correlate(fl, fl, 'full')[len(fl) - 1:]
    lags = np.arange(len(ac)); bpm = 60 * fps / np.maximum(lags, 1); ok = (bpm > 70) & (bpm < 170)
    T = lags[ok][np.argmax(ac[ok])] / fps; best = None
    for per in np.linspace(T * 0.98, T * 1.02, 120):
        for ph in np.linspace(0, per, 48, endpoint=False):
            idx = ((ph + np.arange(0, len(a) / sr - 1, per)) * fps).astype(int); idx = idx[idx < len(fl)]
            sc = fl[idx].sum()
            if best is None or sc > best[0]: best = (sc, per, ph)
    return best[1], best[2]

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('da'); ap.add_argument('--max', type=float, default=0.15)
    ap.add_argument('--lock', default=''); ap.add_argument('--dry', action='store_true'); a = ap.parse_args()
    E = load_json(os.path.join(a.da, 'edit.json')); A = load_json(os.path.join(a.da, 'ads.json'))
    cfg = A.get('audio', {}); music = cfg.get('music', DEFAULT_MUSIC)
    if music is False: sys.exit('không có nhạc → không cần snap')
    from mix import MUSIC_LIB, music_lib
    if music in MUSIC_LIB:
        nm = music; music = music_lib(nm)
        if 'drop' not in cfg and A.get('hook'):
            h = A['hook']; cfg = dict(cfg, drop={'track': MUSIC_LIB[nm][1], 'video': h['price_t'] + float(h.get('count', 0) or 0)})
    if 'drop' in cfg: mi = cfg['drop']['track'] - cfg['drop']['video']
    elif 'music' not in cfg and A.get('hook'):
        h = A['hook']; mi = 8.1 - (h['price_t'] + float(h.get('count', 0) or 0))
    else: mi = cfg.get('music_in', 0.0)
    per, ph = beat_grid(music)
    ph_v = (ph - max(0, mi)) % per
    print(f'· nhạc {60 / per:.1f} BPM · phách đầu trên video {ph_v:.3f}s')
    locks = [float(x) for x in a.lock.split(',') if x]
    br = sorted(E.get('broll', []), key=lambda b: b['t'])
    bounds = sorted({round(v, 3) for b in br for v in (b['t'], b['t'] + b['d'])})
    def snap(x):
        if any(abs(x - l) < 0.03 for l in locks): return x
        k = round((x - ph_v) / per); xb = ph_v + k * per
        if abs(xb - x) <= a.max: return round(xb, 3)
        k2 = round((x - ph_v) / (per / 2)); xh = ph_v + k2 * per / 2
        return round(xh, 3) if abs(xh - x) <= a.max else x
    mp = {x: snap(x) for x in bounds}
    durs = {it['id']: it['dur'] for it in load_json(os.path.join(a.da, 'broll', 'index.json'), {}).get('items', [])}
    moved = 0
    for b in br:
        s0, e0 = b['t'], b['t'] + b['d']; s1, e1 = mp.get(round(s0, 3), s0), mp.get(round(e0, 3), e0)
        if e1 - s1 < 0.4: s1, e1 = s0, e0
        sp = b.get('speed', 1.0); i1 = b.get('in', 0) + (s1 - s0) * sp
        if i1 < 0: i1 = 0
        dur = durs.get(str(b['src']))
        if dur and i1 + (e1 - s1) * sp > dur - 0.02:       # vượt độ dài clip → giữ phần cuối, dời in sớm hơn
            i1 = max(0, dur - 0.02 - (e1 - s1) * sp)
            if i1 + (e1 - s1) * sp > dur - 0.02: s1, e1, i1 = s0, e0, b.get('in', 0)
        if (s1, e1) != (s0, e0): moved += 1
        b['t'], b['d'], b['in'] = round(s1, 3), round(e1 - s1, 3), round(i1, 3)
    for tr in A.get('transitions', []):
        tr[0] = mp.get(round(tr[0], 3), tr[0])
    print(f'· dời {moved}/{len(br)} cảnh B-roll về phách (tối đa ±{a.max}s)')
    for x in bounds:
        if mp[x] != x: print(f'   {x:7.3f} → {mp[x]:7.3f} ({mp[x] - x:+.3f})')
    if a.dry: return
    for n, d in (('edit.json', E), ('ads.json', A)):
        p = os.path.join(a.da, n); shutil.copy(p, p.replace('.json', '_prebeat.json'))
        json.dump(d, open(p, 'w'), ensure_ascii=False, indent=1)
    print('✓ đã ghi edit.json, ads.json (bản cũ: *_prebeat.json) → chạy lại base/draft')

if __name__ == '__main__':
    main()
