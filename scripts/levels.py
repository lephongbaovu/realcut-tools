# realcut levels DA [--video fx_draft.mp4] — đo riêng giọng / nhạc / SFX (xuất lớp trước loudnorm), so với mức anh Vũ chốt
import sys, os, json, subprocess, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
da = sys.argv[1]; vid = sys.argv[sys.argv.index('--video') + 1] if '--video' in sys.argv else None
def mom(path):
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-loglevel', 'verbose', '-i', path, '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    rows = []
    for l in r.splitlines():
        if 'Parsed_ebur128' in l and ' t:' in l and ' M:' in l:
            try:
                t = float(l.split(' t:')[1].split()[0]); mv = l.split(' M:')[1].split()[0]; rows.append((t, float(mv) if mv[0] in '-0123456789' else -120.0))
            except Exception: pass
    I = [l for l in r.splitlines() if l.strip().startswith('I:')]
    return np.array(rows), (I[-1].split()[1] if I else '?')
res = {}
for st in ('voice', 'music', 'sfx'):
    out = os.path.join(da, 'qc', f'stem_{st}.wav'); os.makedirs(os.path.dirname(out), exist_ok=True)
    env = dict(os.environ, REALCUT_STEM=st)
    subprocess.run([sys.executable, '-X', 'utf8', os.path.join(HERE, 'mix.py'), da, '--out', out] + (['--video', vid] if vid else []), env=env, capture_output=True)
    res[st] = mom(out)
ev = json.load(open(os.path.join(da, 'qc', 'stem_sfx.wav.events.json')))
v, Iv = res['voice']; m, Im = res['music']; s, Is = res['sfx']; t = v[:, 0]; vm = v[:, 1]
mm = np.interp(t, m[:, 0], m[:, 1], right=-120); sm = np.interp(t, s[:, 0], s[:, 1], right=-120); sp = vm > -24
L = [f'Giọng {Iv} LUFS · Nhạc {Im} LUFS · SFX {Is} LUFS (lớp trước loudnorm; tổng xuất −14 LUFS)',
     f'Nhạc dưới giọng khi nói: {np.median(vm[sp] - mm[sp]):.1f} dB (chuẩn ~15 dB; mở đầu có thể ~11 dB)']
for a in range(0, int(t[-1]) + 1, 10):
    w = (t >= a) & (t < a + 10) & sp
    if w.any(): L.append(f'  {a:3d}–{a + 10:3d}s: nhạc dưới giọng {np.median(vm[w] - mm[w]):5.1f} dB')
L.append('SFX dưới giọng (chuẩn: whoosh 4–7 dB, tiếng nhấn 5–10 dB; < 3 dB là to quá, > 12 dB là chìm):')
for te, nm in ev:
    w = (t >= te - 0.1) & (t <= te + 0.9); vw = (t >= te - 1.5) & (t <= te + 1.5) & sp
    if w.any() and vw.any():
        d = np.median(vm[vw]) - sm[w].max(); flag = '  ⚠ to' if d < 3 else ('  ⚠ chìm' if d > 12 else '')
        L.append(f'  {te:6.2f}s {nm[:22]:22s} {d:5.1f} dB{flag}')
txt = '\n'.join(L); open(os.path.join(da, 'qc', 'levels.txt'), 'w').write(txt); print(txt)
