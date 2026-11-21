"""realcut · tầng C — âm thanh: giọng (lọc + nén) + nhạc năng lượng (né giọng, drop trùng câu giá) + SFX thưa → loudnorm −14 LUFS.
  python mix.py DA [--video DA/fx.mp4] [--out DA/final.mp4]
Cấu hình trong ads.json → "audio" (reference/schema.md). Thiếu file SFX → tự tổng hợp whoosh/hit/shimmer (không bản quyền).
"""
import argparse, os, subprocess, wave
import numpy as np
from common import load_json, probe, die

SR = 48000

def decode(path, sr=22050):
    b = subprocess.run(['ffmpeg', '-v', 'error', '-i', path, '-ac', '1', '-ar', str(sr), '-f', 's16le', '-'], capture_output=True).stdout
    return np.frombuffer(b, np.int16).astype(np.float32) / 32768, sr

def peak_time(path):
    """giây đỉnh năng lượng của SFX — để đỉnh rơi đúng mốc."""
    x, sr = decode(path)
    if len(x) == 0: return 0.0
    hop = sr // 100
    env = np.sqrt(np.convolve(x ** 2, np.ones(hop) / hop, mode='same'))
    return float(np.argmax(env)) / sr

def write_wav(path, x, sr=SR):
    x = np.clip(x, -1, 1)
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr); w.writeframes((x * 32767).astype(np.int16).tobytes())

def synth_ranh(path, d=1.0):
    """tiếng chạy viền ranh giới (như vucut): 'vút' quét 0.1 s 0.9→14.6 kHz + lấp lánh nốt cao rung ~37 Hz suốt lúc viền vẽ."""
    sr = SR; t = np.arange(int(sr * .1)) / sr; f = 900 * (14600 / 900) ** (t / .1)
    sw = np.sin(2 * np.pi * np.cumsum(f) / sr) * np.sin(np.pi * t / .1) ** .5
    t2 = np.arange(int(sr * d)) / sr; Pk = [(5286, -18.4), (7048, 0), (9984, -3.9), (10573, -26.7), (11160, -21.6), (11747, -3.6), (13509, -6.1)]
    sh = sum(10 ** (g / 20) * np.sin(2 * np.pi * fr * t2 + k) for k, (fr, g) in enumerate(Pk)) * (.25 + .75 * (.5 + .5 * np.cos(2 * np.pi * 36.7 * t2)))
    sh *= np.minimum(1, t2 / .01) * np.minimum(1, (d - t2) / .04)
    x = np.concatenate([sw / np.abs(sw).max() * .8, sh / np.abs(sh).max()]); write_wav(path, x / np.abs(x).max() * .89)

def synth_count(path, d=0.9, n=24):
    """tiếng số chạy (như vucut): tiếng tách dày dần thưa theo đường ease-out + chốt chuông sáng + đệm trầm — đặt đầu file = lúc số bắt đầu chạy."""
    sr = SR; rng = np.random.default_rng(7); L = int(sr * (d + 1.1)); x = np.zeros(L)
    ts = [d * (1 - (1 - k / (n + 1)) ** (1 / 2)) for k in range(1, n + 1)]          # khớp số chạy 1-(1-t)^2
    for k, t in enumerate(ts):
        m = np.arange(int(sr * .018)) / sr; f = 2600 + 1400 * k / n
        c = (np.sin(2 * np.pi * f * m) * .6 + rng.standard_normal(len(m)) * .4) * np.exp(-m * 380)
        a = int(t * sr); x[a:a + len(c)] += c * (.45 + .25 * k / n)
    m = np.arange(int(sr * 1.0)) / sr
    bell = sum(g * np.sin(2 * np.pi * f * m) * np.exp(-m * dk) for f, g, dk in [(1568, 1, 4.5), (2352, .55, 6), (3136, .35, 8), (4704, .18, 11)])
    th = np.sin(2 * np.pi * np.cumsum(90 + 60 * np.exp(-m * 40)) / sr) * np.exp(-m * 14) * .9
    a = int(d * sr); seg = (bell * .6 + th)[:L - a]; x[a:a + len(seg)] += seg
    write_wav(path, x / np.abs(x).max() * .89)

def synth(kind, path):
    """SFX tổng hợp: whoosh (nhiễu quét), hit (boom trầm), shimmer (lấp lánh cao)."""
    rng = np.random.default_rng(7)
    if kind == 'whoosh':
        n = int(SR * 0.7); t = np.arange(n) / SR; x = rng.normal(0, 1, n)
        out = np.zeros(n); y = 0.0
        for i in range(n):                       # lọc thông thấp quét lên rồi xuống
            f = 0.02 + 0.25 * np.sin(np.pi * t[i] / 0.7) ** 2
            y += f * (x[i] - y); out[i] = y
        out *= np.sin(np.pi * t / 0.7) ** 2 * 1.6
    elif kind == 'hit':
        n = int(SR * 1.2); t = np.arange(n) / SR
        out = np.sin(2 * np.pi * (55 + 40 * np.exp(-t * 8)) * t) * np.exp(-t * 3.2) * 0.9
        out += rng.normal(0, 1, n) * np.exp(-t * 40) * 0.25
    elif kind == 'route':                         # vệt đường chạy: tiếng gió mảnh quét lên, sáng dần
        n = int(SR * 1.1); t = np.arange(n) / SR; x = rng.normal(0, 1, n); out = np.zeros(n); y = 0.0; y2 = 0.0
        for i in range(n):
            f = 0.03 + 0.22 * (t[i] / 1.1) ** 1.3
            y += f * (x[i] - y); y2 += 0.5 * (y - y2); out[i] = y - y2
        out *= np.sin(np.pi * np.clip(t / 1.1, 0, 1)) ** 1.5 * 3.2
        out += np.sin(2 * np.pi * (520 + 380 * t / 1.1) * t) * 0.05 * np.sin(np.pi * t / 1.1) ** 2
    elif kind == 'pop':                           # thẻ km bật ra: tiếng "ting" mềm
        n = int(SR * 0.9); t = np.arange(n) / SR; out = np.zeros(n)
        for f, a_ in ((1568, 0.5), (2349, 0.28), (3136, 0.12)):
            out += a_ * np.sin(2 * np.pi * f * t) * np.exp(-t * 6.5)
        out += np.sin(2 * np.pi * 180 * t) * np.exp(-t * 30) * 0.35
        out *= np.minimum(1, t / 0.004) * 0.55
    elif kind == 'out':                           # camera lùi ra toàn cảnh
        n = int(SR * 0.9); t = np.arange(n) / SR; x = rng.normal(0, 1, n); out = np.zeros(n); y = 0.0
        for i in range(n):
            f = 0.2 - 0.17 * t[i] / 0.9
            y += f * (x[i] - y); out[i] = y
        out *= np.sin(np.pi * t / 0.9) ** 2 * 1.4
    else:  # shimmer
        n = int(SR * 1.0); t = np.arange(n) / SR; out = np.zeros(n)
        for f in (2637, 3136, 3951, 4699):
            out += np.sin(2 * np.pi * f * t + rng.random() * 6) * np.exp(-((t - 0.25) / 0.22) ** 2)
        out *= 0.18
    write_wav(path, out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('da'); ap.add_argument('--video'); ap.add_argument('--out')
    a = ap.parse_args()
    A = load_json(os.path.join(a.da, 'ads.json'), {}); cfg = A.get('audio', {})
    if 'music' not in cfg:                        # mặc định anh Vũ duyệt: "Life is a Dream" (Mixkit 837), drop đúng lúc chốt giá
        cfg = dict(cfg); mp = os.path.join(os.path.expanduser('~'), '.realcut', 'music', 'mixkit_837_life_is_a_dream.mp3')
        if not os.path.exists(mp):
            os.makedirs(os.path.dirname(mp), exist_ok=True)
            subprocess.run(['curl', '-sL', '-m', '120', '-o', mp, 'https://assets.mixkit.co/music/837/837.mp3'])
        if os.path.exists(mp) and os.path.getsize(mp) > 100000:
            cfg['music'] = mp; cfg.setdefault('pre_drop_gain', 2.0)
            hk = A.get('hook')
            if 'drop' not in cfg and hk: cfg['drop'] = {'track': 8.1, 'video': hk['price_t'] + float(hk.get('count', 0) or 0)}
            print('  · nhạc mặc định: Life is a Dream (Mixkit)')
        else: print('  ⚠ không tải được nhạc mặc định — xuất không nhạc')
    elif cfg.get('music') is False: cfg = dict(cfg); cfg.pop('music')   # "music": false = không nhạc
    vid = a.video or os.path.join(a.da, 'fx.mp4')
    if not os.path.exists(vid): die(f'Không thấy {vid} — chạy `fx` trước')
    out = a.out or os.path.join(a.da, 'final.mp4')
    dur = probe(vid)['dur']
    voice = cfg.get('voice', os.path.join(a.da, 'cut.mp4'))
    sfxd = os.path.join(a.da, 'sfx_synth'); os.makedirs(sfxd, exist_ok=True)
    lib = dict(cfg.get('sfx_lib', {}))
    for k in ('whoosh', 'hit', 'shimmer', 'out'):
        if not lib.get(k) or not os.path.exists(lib[k]):
            p = os.path.join(sfxd, k + '.wav')
            if not os.path.exists(p): synth(k, p)
            lib[k] = p
    # sự kiện SFX: tự động theo cấu trúc + danh sách tay
    ev = []
    if cfg.get('sfx_auto', True):
        sd = {'whoosh': -24, 'hit': -17, 'shimmer': -20, 'end_hit': -17}; sd.update(cfg.get('sfx_db', {}))   # chỉnh mức SFX tự động
        for t, _ in A.get('transitions', []): ev.append(('whoosh', t, sd['whoosh']))
        h = A.get('hook')
        if h and not h.get('count'): ev.append(('hit', h['price_t'], sd['hit']))
        o = A.get('offer')
        if o: ev.append(('shimmer', o['t0'] + 0.35, sd['shimmer']))
        if A.get('end'): ev.append(('hit', A['end']['t'] + 0.2, sd['end_hit']))
    ev.sort(key=lambda e: e[1])
    keep, last = [], -9                       # thưa: ≥ 2.5 s giữa 2 SFX tự động (trừ hit)
    for e in ev:
        if e[0] == 'hit' or e[1] - last >= 2.5:
            keep.append(e); last = e[1]
    # tiếng kết nối của bản đồ (mốc do mapfx ghi) — giữ hết, không lọc thưa
    E = load_json(os.path.join(a.da, 'edit.json'), {})
    def ranh(d):
        pth = os.path.join(sfxd, f'ranh_{d:.2f}.wav')
        if not os.path.exists(pth): synth_ranh(pth, d)
        return pth
    rdb = cfg.get('ranh_db', -26)
    hk = A.get('hook')
    if hk and hk.get('count') and cfg.get('sfx_auto', True):    # giá chạy số: tiếng đếm + chốt chuông (thay tiếng hit)
        cp_ = os.path.join(sfxd, f"count_{float(hk['count']):.2f}.wav")
        if not os.path.exists(cp_): synth_count(cp_, float(hk['count']), n=max(18, int(float(hk['count']) * 16)))
        keep.append((cp_, hk['price_t'], cfg.get('sfx_db', {}).get('count', -17)))
    for pl in A.get('plot', []):                # đồ hoạ lô đất: tiếng chạy viền khi ranh được vẽ
        keep.append((ranh(pl.get('draw', 0.8)), pl['t0'], rdb))
    if cfg.get('map_sfx', True):
        lv = {'out': cfg.get('sfx_db', {}).get('out', -27)}
        for b in E.get('broll', []):
            src = str(b.get('src', ''))
            mp = os.path.join(a.da, 'broll_916', os.path.splitext(os.path.basename(src))[0] + '_sfx.json')
            if not os.path.exists(mp): continue
            for e in load_json(mp, {}).get('events', []):
                tt = b['t'] + e['t'] - b.get('in', 0)
                if not (b['t'] - 0.05 <= tt <= b['t'] + b['d']): continue
                if e['kind'] == 'route': keep.append((ranh(e.get('d', 1.0)), tt - 0.05, rdb))   # viền đường chạy = tiếng ranh
                elif e['kind'] in lv: keep.append((e['kind'], tt, lv[e['kind']]))
    for e in cfg.get('sfx', []):               # danh sách tay: giữ hết
        keep.append((e['file'], e['t'], e.get('db', -12)))
    keep.sort(key=lambda e: e[1])
    inputs = ['-i', vid, '-i', voice]
    vc = cfg.get('voice_clarity', 0)          # 1 = giọng rõ hơn: bớt ù 250 Hz, sáng 3–5 kHz, nén chặt hơn (anh Vũ duyệt 21/11)
    veq = ('equalizer=f=250:t=q:w=1.0:g=-2.5,equalizer=f=3200:t=q:w=1.2:g=4,equalizer=f=5500:t=q:w=1.5:g=1.5,'
           'acompressor=threshold=-24dB:ratio=4:attack=4:release=100:makeup=3,') if vc else 'equalizer=f=3000:t=q:w=1.2:g=2,'
    fc = ['[1:a]highpass=f=80,acompressor=threshold=-20dB:ratio=3:attack=5:release=120:makeup=2,'
          + veq + f"volume={cfg.get('voice_db', 0)}dB,aresample=48000,apad" + (',asplit=2[vo][vsc]' if cfg.get('music') else '[vo]')]
    mix = ['[vo]']
    if cfg.get('music'):
        mi = cfg.get('music_in', 0.0)
        if 'drop' in cfg:                     # {"track": giây drop trong bài, "video": giây cần drop}
            mi = cfg['drop']['track'] - cfg['drop']['video']
        inputs += ['-ss', f'{max(0, mi):.3f}', '-i', cfg['music']]
        g = cfg.get('music_gain', 0.2); endt = A.get('end', {}).get('t', dur)   # anh Vũ duyệt: nhạc chỉ làm nền dưới giọng
        vol = f"if(lt(t,{endt}),{g},{g}+0.30*min(1,(t-{endt})/0.8))"
        pg = cfg.get('pre_drop_gain')                # nâng phần dạo nhạc trước drop (dạo thường rất nhỏ) — giữ người xem 3 s đầu
        if pg and 'drop' in cfg:
            dv = cfg['drop']['video']; vol = f"({vol})*if(lt(t,{dv - 0.15:.2f}),{pg},1)"
        fc.append(f"[2:a]atrim=0:{dur:.2f},asetpts=PTS-STARTPTS,aresample=48000,volume='{vol}':eval=frame,"
                  f"afade=t=in:d=0.25,afade=t=out:st={dur - 1.6:.2f}:d=1.6[mu]")
        fc.append(f"[mu][vsc]sidechaincompress=threshold={cfg.get('duck_threshold', 0.05)}:ratio={cfg.get('duck_ratio', 3.5)}:attack=20:release=350:makeup=1[mud]")   # duck: nhạc lùi khi có giọng
        mix.append('[mud]')
    n0 = 3 if cfg.get('music') else 2
    labels = []
    for i, (f, t, db) in enumerate(keep):
        path = lib.get(f, f)
        if not os.path.exists(path): print('  ⚠ bỏ SFX thiếu file:', path); continue
        inputs += ['-i', path]
        st = max(0.0, t - (0 if os.path.basename(path).startswith(('ranh_', 'count_')) else peak_time(path))); ms = int(st * 1000)
        fc.append(f'[{n0 + len(labels)}:a]aresample=48000,volume={db}dB,adelay={ms}|{ms}[e{len(labels)}]')
        labels.append(f'[e{len(labels)}]')
    if labels:
        fc.append(''.join(labels) + f'amix=inputs={len(labels)}:normalize=0:dropout_transition=0[sfx]'); mix.append('[sfx]')
    lufs = cfg.get('lufs', -14)
    fc.append(''.join(mix) + f'amix=inputs={len(mix)}:normalize=0:duration=first,loudnorm=I={lufs}:TP=-1.2:LRA=9,aresample=48000[aout]')
    cmd = ['ffmpeg', '-v', 'error', '-y'] + inputs + ['-filter_complex', ';'.join(fc), '-map', '0:v', '-map', '[aout]',
           '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-movflags', '+faststart', '-t', f'{dur:.2f}', out]
    subprocess.run(cmd, check=True)
    print(f'✓ {out} · {len(labels)} SFX · {"có nhạc" if cfg.get("music") else "KHÔNG nhạc (thêm audio.music)"}')

if __name__ == '__main__':
    main()
