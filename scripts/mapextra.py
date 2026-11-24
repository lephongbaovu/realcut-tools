# realcut · đồ hoạ bản đồ mở rộng (anh Vũ chốt 24/11/2026 — video 15 lô Ea Ning)
#   python3 mapextra.py DA [pair|ranh|zone|cards|all]      cấu hình: DA/extras.json (xem reference/schema.md mục 9)
#   pair  : ghép 2 hình (toàn cảnh + sơ đồ phân lô) dọc 9:16, nền than ấm, khung viền vàng, trượt vào mượt
#   ranh  : bản đồ vệ tinh Google ranh giới xã (dữ liệu 2025), line sáng chạy ranh → zoom liền mạch vào lô, khung cuối = khung đầu bản đồ MAP
#   zone  : khu quy hoạch trên vệ tinh: line sáng chạy ranh (tiếng ranh) → vạch sáng quét lộ phối cảnh ghép trong ranh
#   cards : thẻ hình/video bật ra từ điểm đến khi đường đi chạy tới (MAP*), dây nối vàng, tự né đường/thẻ km
#   ghim BĐS dùng chung: ghim vàng + vòng sáng loang; khung sơ đồ phân lô (extras.thumb) bung ra từ ghim theo lịch rồi thu về
import sys, os, math, json, glob, subprocess, unicodedata
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import numpy as np, cv2
from PIL import Image
import textfx as T, mapfx
from common import load_json, save_json
Image.MAX_IMAGE_PIXELS = None
W, H, FPS = 1080, 1920, 30
GOLD = (110, 200, 240)                       # BGR
TILES = os.path.join(os.path.expanduser('~'), '.realcut', 'tiles')

def ease(x): x = max(0., min(1., x)); return x * x * (3 - 2 * x)
def eout(x): x = max(0., min(1., x)); return 1 - (1 - x) ** 3
def bgr(sp): sp = dict(sp); sp['rgb'] = np.ascontiguousarray(sp['rgb'][..., ::-1]); return sp
def writer(out):
    return subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                             '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-pix_fmt', 'yuv420p', out], stdin=subprocess.PIPE)
def wz(lat, lon, z):                         # Web Mercator → px ở zoom z
    n = 256 * 2 ** z; s = math.sin(math.radians(lat)); return np.array(((lon + 180) / 360 * n, (0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)) * n))
def latlon(p): v = [float(x) for x in str(p).replace(' ', '').split(',')] if isinstance(p, str) else list(p); return v[0], v[1]
def satellite(z, X0, Y0, X1, Y1):
    """ghép ô vệ tinh Google, chỉnh màu như mapfx (bớt rực để vàng nổi) → (ảnh BGR, gốc px)"""
    os.makedirs(TILES, exist_ok=True)
    tx = range(int(X0) // 256, int(X1) // 256 + 1); ty = range(int(Y0) // 256, int(Y1) // 256 + 1)
    def get(xy):
        x, y = xy; f = os.path.join(TILES, f'g{z}_{x}_{y}.jpg')
        if not os.path.exists(f) or os.path.getsize(f) < 1000:
            subprocess.run(['curl', '-s', '--max-time', '20', '-o', f, f'https://mt{(x + y) % 4}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}'])
        return xy, f
    with ThreadPoolExecutor(16) as ex: fs = list(ex.map(get, [(x, y) for x in tx for y in ty]))
    im = np.zeros((len(ty) * 256, len(tx) * 256, 3), np.uint8)
    for (x, y), f in fs:
        try: im[(y - ty[0]) * 256:(y - ty[0] + 1) * 256, (x - tx[0]) * 256:(x - tx[0] + 1) * 256] = np.asarray(Image.open(f).convert('RGB'))[:, :, ::-1]
        except Exception: pass
    c = im.astype(np.float32); g = c.mean(2, keepdims=True); c = g + (c - g) * 0.78; c = c * np.array((0.83, 0.88, 0.90)) + np.array((0, 4, 6))
    return np.clip(c, 0, 255).astype(np.uint8), np.array((tx[0] * 256, ty[0] * 256), np.float64)

# ───────── ghim BĐS + khung sơ đồ bung ra từ ghim ─────────
class Pin:
    def __init__(self, thumb=None, thumb_w=300):
        self.pin = bgr(T.pin_icon(92)); self.th = bgr(mapfx.thumb_sprite(thumb, thumb_w)) if thumb and os.path.exists(thumb) else None
    @staticmethod
    def vis(t, sched):
        v = 0.0; back = 0.0
        for a, b in sched or []:
            if a <= t <= b: v = max(v, min(1.0, (t - a) / 0.35) if t < b - 0.3 else (b - t) / 0.3)
            if b <= t <= b + 0.3: back = (t - b) / 0.3
        return max(0.0, min(1.0, v)), back
    def draw(self, f, x, y, t, op=1.0, sched=()):
        if op <= 0.01: return f
        tv, back = self.vis(t, sched)
        gl = np.zeros_like(f, dtype=np.float32)
        for i in range(3):                                            # vòng sáng loang ra ngoài
            ph = (t / 1.25 + i / 3) % 1.0; r = int(14 + 95 * ph); a = (1 - ph) ** 1.5
            cv2.circle(gl, (int(x), int(y)), r, (90 * a, 205 * a, 255 * a), 3, cv2.LINE_AA)
        cv2.circle(gl, (int(x), int(y)), 22, (60, 150, 200), -1, cv2.LINE_AA)
        gl = cv2.GaussianBlur(gl, (0, 0), 3) * 1.4 + cv2.GaussianBlur(gl, (0, 0), 14) * 1.2
        f = np.clip(f.astype(np.float32) + gl * op, 0, 255).astype(np.uint8)
        pe = op * (1 - min(1, tv * 1.6))
        if pe > 0.01:
            pb = 1 + 0.25 * math.sin(math.pi * back); ps = self.pin if pb == 1 else dict(self.pin, **mapfx._scale_sprite(self.pin, pb))
            T.over(f, ps, x - ps['w'] / 2, y - ps['h'] * 0.97, pe)
        if tv > 0.001 and self.th is not None:
            k = 1 - (1 - tv) ** 3; sc = max(0.03, k * (1 + 0.06 * math.sin(math.pi * tv))); TH = self.th
            sp = dict(TH, **mapfx._scale_sprite(TH, sc))
            x0 = min(max(x - sp['w'] / 2, 0.06 * W), 0.94 * W - sp['w']); y0 = y - 34 - TH['h'] / 2 * sc - sp['h'] / 2
            tri = np.array([[x - 14 * sc, y0 + sp['h'] - 20 * sc], [x + 14 * sc, y0 + sp['h'] - 20 * sc], [x, y - 4]], np.int32)
            a_ = min(1, tv * 1.5) * op; lay = f.copy(); cv2.fillConvexPoly(lay, tri, GOLD, cv2.LINE_AA); f = cv2.addWeighted(lay, a_, f, 1 - a_, 0)
            T.over(f, sp, x0, y0, a_)
        return f

# ───────── PAIR: 2 hình ghép dọc ─────────
def do_pair(da, c, X):
    U = lambda p: p if os.path.isabs(p) else os.path.join(da, p)
    D = float(c.get('d', 8.0)); M_ = 44; PW = W - 2 * M_
    def load(p, crop):
        im = Image.open(U(p)).convert('RGB')
        if crop: w, h = im.size; im = im.crop((int(w * crop[0]), int(h * crop[1]), int(w * crop[2]), int(h * crop[3])))
        return np.asarray(im.resize((int(PW * 1.08), int(im.height * PW * 1.08 / im.width)), Image.LANCZOS))[:, :, ::-1].copy()
    A = load(c['top'], c.get('top_crop')); B = load(c['bottom'], c.get('bottom_crop'))
    hA, hB = int(A.shape[0] / 1.08), int(B.shape[0] / 1.08); gap = 62; yA = int(H * c.get('y', 0.326)); yB = yA + hA + gap
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32); bg = np.zeros((H, W, 3), np.float32); bg[:] = (30, 34, 40)     # than ấm
    r = np.sqrt(((xx - W / 2) / W) ** 2 + ((yy - H * 0.55) / H) ** 2); bg = (bg * np.clip(1.25 - 1.1 * r, 0.55, 1.15)[..., None]).clip(0, 255).astype(np.uint8)
    labs = [bgr(T.sprite(T.nfc(s), 'semibold', 26, 'cream', tracking=0.26)) for s in c.get('labels', ['TOÀN CẢNH', 'SƠ ĐỒ PHÂN LÔ'])]
    def panel(src, h, s):
        Mx = np.float32([[s / 1.08, 0, PW / 2 - s / 1.08 * src.shape[1] / 2], [0, s / 1.08, h / 2 - s / 1.08 * src.shape[0] / 2]])
        return cv2.warpAffine(src, Mx, (PW, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REFLECT)
    out = os.path.join(da, 'broll_916', c.get('id', 'PAIR') + '.mp4'); p = writer(out)
    for i in range(int(D * FPS)):
        t = i / FPS; u = t / D; f = bg.copy()
        for (src, h, y, L, t0, dirn, s0, s1) in ((A, hA, yA, labs[0], 0.0, -1, 1.0, 1.06), (B, hB, yB, labs[1], 0.12, 1, 1.06, 1.0)):
            e = eout((t - t0) / 0.55); dx = int(round(dirn * (1 - e) * 140))
            im = panel(src, h, s0 + (s1 - s0) * u).copy(); cv2.rectangle(im, (1, 1), (PW - 2, h - 2), GOLD, 3, cv2.LINE_AA)
            x0 = M_ + dx; xa, xb = max(0, x0), min(W, x0 + PW)
            if xb > xa and e > 0:
                roi = f[y:y + h, xa:xb].astype(np.float32); f[y:y + h, xa:xb] = (roi * (1 - e) + im[:, xa - x0:xb - x0] * e).astype(np.uint8)
            T.over(f, L, x0 + 4, y - L['h'] - 12, e)
        p.stdin.write(f.tobytes())
    p.stdin.close(); p.wait(); print('  ✓', out, f'{D}s')

# ───────── RANH: ranh giới xã → zoom liền mạch vào khung đầu MAP ─────────
def ward_ring(name):
    repo = os.path.join(os.path.expanduser('~'), '.realcut', 'vpd'); base = os.path.join(repo, 'json', 'geojson', '66_dak_lak')
    if not os.path.isdir(base):
        subprocess.run(f'GIT_LFS_SKIP_SMUDGE=1 git clone -q --depth 1 --filter=blob:none --sparse https://github.com/ThangLeQuoc/vietnamese-provinces-database {repo}', shell=True)
        subprocess.run(['git', '-C', repo, 'sparse-checkout', 'set', 'json/geojson/66_dak_lak'])
    key = unicodedata.normalize('NFD', name.lower().replace('đ', 'd')).encode('ascii', 'ignore').decode().replace('đ', 'd').replace(' ', '_')
    fs = [f for f in glob.glob(os.path.join(base, 'wards', '*.geojson')) if os.path.basename(f).split('_', 1)[1].startswith(key)]
    if not fs: sys.exit(f'không thấy ranh xã/phường "{name}" trong dữ liệu Đắk Lắk 2025')
    d = json.load(open(fs[0], encoding='utf-8')); g = (d['features'][0] if 'features' in d else d)['geometry']
    return g['coordinates'][0] if g['type'] == 'Polygon' else max((p[0] for p in g['coordinates']), key=len)
def do_ranh(da, c, X):
    D = float(c.get('d', 2.6)); TD0, TD1, TZ0, XF = 0.12, 1.30, 1.25, 0.30
    spec = [s for s in load_json(os.path.join(da, 'map.json'))['maps'] if s['id'] == c.get('map', 'MAP1')][0]
    m = mapfx.Map(spec, load_json(os.path.join(da, 'geo_cache.json'), {}), quiet=True); m.layout(); m.durs(); m.canvas(); m.sprites(); m.place(); m.camera()
    F0 = np.ascontiguousarray(m.frame(0)[..., ::-1]); (cx, cy), s1 = m.cam_at(0); bc = np.array(m.bc)
    wc = np.array(m.cw) + (np.array((cx, cy)) - bc) / m.k
    ring = ward_ring(c['xa']); lat0, lon0 = latlon(spec['home']['at'])
    Z1, Z2 = 15, 17; R1 = np.array([wz(la, lo, Z1) for lo, la in ring])
    lo_, hi_ = R1.min(0), R1.max(0); c0 = (lo_ + hi_) / 2; s0 = H * 0.46 / (hi_[1] - lo_[1]); fc0 = np.array((W / 2, H * 0.58))
    send = m.k * s1 / 2 ** Z1 / 256; cend = wc * 256 * 2 ** Z1
    A, oA = satellite(Z1, c0[0] - W / 2 / s0 - 200, c0[1] - 0.58 * H / s0 - 200, c0[0] + W / 2 / s0 + 200, c0[1] + 0.42 * H / s0 + 200)
    sw = 2 ** (Z2 - Z1); hwd = (W / 2) / (1.1 / sw) + 300; cz2 = cend * sw
    B, oB = satellite(Z2, cz2[0] - hwd, cz2[1] - hwd * 1.8, cz2[0] + hwd, cz2[1] + hwd * 1.8)
    mask = np.zeros(A.shape[:2], np.uint8); cv2.fillPoly(mask, [np.int32(R1 - oA)], 255); mA = cv2.GaussianBlur(mask, (0, 0), 6).astype(np.float32) / 255
    Rl = R1 - oA; seg = np.r_[0, np.cumsum(np.linalg.norm(np.diff(Rl, axis=0), axis=1))]; L1 = wz(lat0, lon0, Z1)
    pin = Pin(); out = os.path.join(da, 'broll_916', c.get('id', 'RANH') + '.mp4'); p = writer(out); N = int(round(D * FPS))
    for i in range(N):
        t = i / FPS; u = 0.0 if t < TZ0 else 1 - (1 - min(1.0, (t - TZ0) / (D - TZ0))) ** 3
        sa = s0 * (1 + 0.03 * min(1, t / TZ0)); s = math.exp(math.log(sa) + (math.log(send) - math.log(sa)) * u)
        cc = c0 * (1 - u) + cend * u; fc = fc0 * (1 - u) + bc * u
        MA = np.float32([[s, 0, fc[0] - s * (cc[0] - oA[0])], [0, s, fc[1] - s * (cc[1] - oA[1])]])
        fA = cv2.warpAffine(A, MA, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
        dk = 1 - ease((u - 0.35) / 0.45); mk = cv2.warpAffine(mA, MA, (W, H), flags=cv2.INTER_LINEAR)[..., None]
        fA = fA * (1 - dk * 0.58 * (1 - mk)); bw = ease((s - 1.0) / 0.6)
        if bw > 0:
            sb = s / sw; cb = cc * sw; MB = np.float32([[sb, 0, fc[0] - sb * (cb[0] - oB[0])], [0, sb, fc[1] - sb * (cb[1] - oB[1])]])
            fA = fA * (1 - bw) + cv2.warpAffine(B, MB, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32) * bw
        vg = ease((u - 0.5) / 0.5); fA = fA * (1 - vg + vg * m.vig); f = np.clip(fA, 0, 255).astype(np.uint8)
        lop = 1 - ease((u - 0.45) / 0.35); k = ease((t - TD0) / (TD1 - TD0)) * seg[-1]
        if k > 0 and lop > 0:
            mm = int(np.searchsorted(seg, k)); pts = np.int32((Rl[:max(2, mm + 1)] * s + MA[:, 2]) * 4)
            g_ = np.zeros_like(f); cv2.polylines(g_, [pts], False, (90, 210, 255), 16, cv2.LINE_AA, 2); g_ = cv2.GaussianBlur(g_, (0, 0), 9)
            l_ = f.copy(); cv2.polylines(l_, [pts], False, (150, 235, 255), 4, cv2.LINE_AA, 2); f = cv2.addWeighted(cv2.add(l_, g_), lop, f, 1 - lop, 0)
        pl = (L1 - oA) * s + MA[:, 2]; po = ease((t - TD1 + 0.25) / 0.3) * (1 - ease((t - (D - XF - 0.1)) / XF))
        f = pin.draw(f, pl[0], pl[1], t, po)
        xf = ease((t - (D - XF)) / XF)
        if xf > 0: f = cv2.addWeighted(F0, xf, f, 1 - xf, 0)
        if i == N - 1: f = F0
        p.stdin.write(np.ascontiguousarray(f).tobytes())
    p.stdin.close(); p.wait(); save_json(out.replace('.mp4', '_sfx.json'), {'events': [{'kind': 'route', 't': TD0, 'd': round(TD1 - TD0, 2)}]})
    print('  ✓', out, f'{D}s · khung cuối = khung đầu {c.get("map", "MAP1")} (nối không thấy cắt)')

# ───────── ZONE: khu quy hoạch + phối cảnh quét lộ ─────────
def do_zone(da, c, X):
    U = lambda p: p if os.path.isabs(p) else os.path.join(da, p)
    D = float(c['d']); TD0, TD1 = c.get('t_draw', [1.0, 2.9]); R0, R1 = c.get('t_reveal', [3.25, 4.25]); F0, F1 = TD1 - 0.3, TD1 + 0.3
    z = 17; pts = np.array([wz(*latlon(q), z) for q in c['poly']]); L = wz(*latlon(c['home']), z)
    allp = np.vstack([pts, L[None]]); c0 = (allp.min(0) + allp.max(0)) / 2; CW, CH = 2000, 3556
    can, o = satellite(z, c0[0] - CW / 2, c0[1] - CH / 2, c0[0] + CW / 2, c0[1] + CH / 2)
    P = pts - o; Lc = L - o; cpoly = P.mean(0)
    pcw = None
    if c.get('image'):
        pc = cv2.imread(U(c['image'])); A = cv2.getAffineTransform(np.float32(c['image_pts']), np.float32([P[i] if isinstance(i, int) else P[list(i)].mean(0) for i in c['poly_pts']]))
        pcw = cv2.warpAffine(pc, A, (can.shape[1], can.shape[0]), flags=cv2.INTER_CUBIC)
        cover = cv2.warpAffine(np.full(pc.shape[:2], 255, np.uint8), A, (can.shape[1], can.shape[0]))
        mask = np.zeros(can.shape[:2], np.uint8); cv2.fillPoly(mask, [np.int32(P)], 255); mask = cv2.min(mask, cover)
        mask = cv2.GaussianBlur(mask, (0, 0), 5).astype(np.float32) / 255
    per = np.r_[0, np.cumsum(np.linalg.norm(np.diff(np.vstack([P, P[:1]]), axis=0), axis=1))]
    lab3 = bgr(T.sprite(T.nfc(c.get('label', 'PHỐI CẢNH MINH HOẠ')), 'semibold', 26, 'cream', tracking=0.22, shadow=0.6))
    pin = Pin(X.get('thumb'), X.get('thumb_w', 300)); s_start = W / CW * 1.12; s_end = s_start * 1.30
    cc0 = np.array((c0[0] - o[0], c0[1] - o[1])); cc1 = cpoly * 0.7 + Lc * 0.3
    out = os.path.join(da, 'broll_916', c.get('id', 'ZONE') + '.mp4'); p = writer(out)
    for i in range(int(round(D * FPS))):
        t = i / FPS; u = ease(t / D) * 0.8 + 0.2 * t / D; s = s_start * (s_end / s_start) ** u; cc = cc0 * (1 - u) + cc1 * u
        M = np.float32([[s, 0, W / 2 - s * cc[0]], [0, s, H * 0.52 - s * cc[1]]])
        f = cv2.warpAffine(can, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT).astype(np.float32)
        ra = min(1.0, max(0.0, (t - R0) / (R1 - R0))) if pcw is not None else 0.0
        Qf = P * s + M[:, 2]; qy0, qy1 = Qf[:, 1].min() - 10, Qf[:, 1].max() + 10
        if ra > 0:                                       # vạch sáng quét từ đỉnh xuống, phối cảnh lộ ra theo vạch
            ye = qy0 + (qy1 - qy0 + 60) * (ra * ra * (3 - 2 * ra)); ramp = np.clip((ye - np.arange(H, dtype=np.float32)) / 60.0, 0, 1)[:, None, None]
            pw = cv2.warpAffine(pcw, M, (W, H), flags=cv2.INTER_LINEAR).astype(np.float32); pm = cv2.warpAffine(mask, M, (W, H), flags=cv2.INTER_LINEAR)[..., None]
            mk = pm * 0.97 * ramp; f = f * (1 - mk) + pw * mk
            if ra < 1:
                band = np.exp(-((np.arange(H, dtype=np.float32) - ye) / 7.0) ** 2)[:, None, None] * pm
                f = f + (band + cv2.GaussianBlur(band[..., 0], (0, 0), 14)[..., None] * 2.2) * np.array((110, 215, 255), np.float32) * 0.9
        fa = 0.28 * ease((t - F0) / (F1 - F0)) * (1 - ease(ra))
        if fa > 0: ov = f.copy(); cv2.fillPoly(ov, [np.int32(Qf)], (40, 170, 235)); f = f * (1 - fa) + ov * fa
        f = np.clip(f, 0, 255).astype(np.uint8); k = ease((t - TD0) / (TD1 - TD0)) * per[-1]
        if k > 0:
            mm = int(np.searchsorted(per, k)); QQ = np.vstack([Qf, Qf[:1]]); sg = QQ[:mm]
            if mm < len(QQ): a_, b_ = QQ[mm - 1], QQ[mm]; uu = (k - per[mm - 1]) / max(1e-6, per[mm] - per[mm - 1]); sg = np.vstack([sg, a_ + (b_ - a_) * uu])
            sg = np.int32(np.round(sg * 4)); glow = np.zeros_like(f); cv2.polylines(glow, [sg], False, (90, 210, 255), 16, cv2.LINE_AA, 2)
            f = cv2.add(f, cv2.GaussianBlur(glow, (0, 0), 8)); cv2.polylines(f, [sg], False, (150, 235, 255), 5, cv2.LINE_AA, 2)
        lx, ly = Lc * s + M[:, 2]; f = pin.draw(f, lx, ly, t, ease(t / 0.4), c.get('thumb_t'))
        if pcw is not None: T.over(f, lab3, 0.93 * W - lab3['w'], ly - 47 - lab3['h'] / 2, ease((t - R0 - 0.3) / 0.5))
        p.stdin.write(f.tobytes())
    p.stdin.close(); p.wait(); save_json(out.replace('.mp4', '_sfx.json'), {'events': [{'kind': 'route', 't': TD0, 'd': round(TD1 - TD0, 2)}]})
    print('  ✓', out, f'{D}s · tiếng quét phối cảnh: thêm audio.sfx shimmer_soft tại t+{R0}')

# ───────── CARDS: thẻ hình/video ở điểm đến ─────────
def do_cards(da, X):
    U = lambda p: p if os.path.isabs(p) else os.path.join(da, p)
    for mid, cards in X.get('cards', {}).items():
        spec = [s for s in load_json(os.path.join(da, 'map.json'))['maps'] if s['id'] == mid][0]
        m = mapfx.Map(spec, load_json(os.path.join(da, 'geo_cache.json'), {}), quiet=True); m.layout(); m.durs(); m.canvas(); m.sprites(); m.place(); m.camera()
        Fx, Fy = m.bc; R_, BD = 18, 4
        def P_at(t, q): (cx, cy), s = m.cam_at(t); return (Fx + (q[0] - cx) * s, Fy + (q[1] - cy) * s)
        def rmask(w, h):
            mk = np.zeros((h, w), np.uint8); cv2.rectangle(mk, (R_, 0), (w - R_, h), 255, -1); cv2.rectangle(mk, (0, R_), (w, h - R_), 255, -1)
            for a_, b_ in [(R_, R_), (w - R_, R_), (R_, h - R_), (w - R_, h - R_)]: cv2.circle(mk, (a_, b_), R_, 255, -1, cv2.LINE_AA)
            return mk
        for j, c in enumerate(cards):
            it = m.items[c['item']]; arr = it['rel'] - 0.12 + it['dur']           # đường chạy tới điểm đến
            nxt = m.items[c['item'] + 1]['rel'] - 0.22 if c['item'] + 1 < len(m.items) else m.d + 0.5
            c.setdefault('t0', round(arr + (0.5 if c['item'] + 1 == len(m.items) and m.t_over < arr + 0.6 else 0.05), 2))
            c.setdefault('t1', round(min(nxt, c['t0'] + 2.0) if nxt < m.d else m.d + 0.5, 2))
            src = U(c['src']); n = int((c['t1'] - c['t0'] + 0.5) * FPS)
            if src.lower().endswith(('.jpg', '.jpeg', '.png')):
                im = cv2.imread(src)
                if c.get('crop'): x0, y0, x1, y1 = c['crop']; im = im[y0:y1, x0:x1]
                c['clip'] = [im]
            else:
                cap = cv2.VideoCapture(src); cap.set(cv2.CAP_PROP_POS_MSEC, c.get('in', 0) * 1000); fs = []
                while len(fs) < n:
                    ok, fr = cap.read()
                    if not ok: break
                    h, w = fr.shape[:2]; th = int(w * 9 / 16)
                    if th <= h: fs.append(fr[(h - th) // 2:(h - th) // 2 + th])
                    else: tw = int(h * 16 / 9); fs.append(fr[:, (w - tw) // 2:(w - tw) // 2 + tw])
                c['clip'] = fs or [np.zeros((90, 160, 3), np.uint8)]
            obst = []
            for i in range(int(c['t0'] * FPS), int(c['t1'] * FPS) + 1):
                t = i / FPS
                for o in m.items[:c['item'] + 1]:
                    pts = [P_at(t, q) for q in o['rf']]
                    for k in range(1, len(pts)):
                        a_, b_ = np.array(pts[k - 1]), np.array(pts[k]); obst += [tuple(a_ + (b_ - a_) * uu) for uu in np.linspace(0, 1, 5)]
                    px, py = P_at(t, o['pf']); cw, ch = o['card']['w'], o['card']['h']
                    for ox, oy in [o.get('off_z', (20, -80)), o.get('off', o.get('off_z', (20, -80)))]:
                        obst += [(px + ox + dx, py + oy + dy) for dx in np.linspace(0, cw, 8) for dy in np.linspace(0, ch, 4)]
                hx, hy = P_at(t, m.hf); obst += [(hx + dx, hy + dy) for dx in range(-60, 61, 20) for dy in range(-110, 30, 20)]
            obst = np.array(obst); best = None
            for PW in range(460, 299, -20):
                PH = int(PW * 9 / 16)
                for y in np.arange(0.16 * H, 0.645 * H - PH, 12):
                    for x in np.arange(0.06 * W, 0.94 * W - PW, 12):
                        mg = 26
                        if ((obst[:, 0] > x - mg) & (obst[:, 0] < x + PW + mg) & (obst[:, 1] > y - mg) & (obst[:, 1] < y + PH + mg)).any(): continue
                        dpx, dpy = P_at((c['t0'] + c['t1']) / 2, it['pf']); d = math.hypot(x + PW / 2 - dpx, y + PH / 2 - dpy)
                        ex_, ey_ = min(max(dpx, x + 20), x + PW - 20), (y if dpy < y else y + PH); cross = 0
                        for u_ in np.linspace(0.15, 1, 10):
                            qx, qy = dpx + (ex_ - dpx) * u_, dpy + (ey_ - dpy) * u_
                            if math.hypot(qx - dpx, qy - dpy) < 45: continue
                            cross += int(((np.abs(obst[:, 0] - qx) < 10) & (np.abs(obst[:, 1] - qy) < 10)).any())
                        sc = PW * 1.5 - d * 1.3 - cross * 400
                        if best is None or sc > best[0]: best = (sc, PW, PH, x, y, cross)
            if best is None: print(f'  ⚠ {mid}: không còn chỗ trống cho thẻ {j}'); c['skip'] = True; continue
            _, c['PW'], c['PH'], c['BX'], c['BY'], cr = best; c['mask'] = rmask(c['PW'], c['PH'])
            if cr and 'stem' not in c: c['stem'] = 'elbow'
            print(f'  · {mid} thẻ {j}: {c["t0"]}–{c["t1"]}s · {c["PW"]}×{c["PH"]} tại ({int(c["BX"])}, {int(c["BY"])})')
        out = os.path.join(da, 'broll_916', mid + '.mp4'); p = writer(out)
        for i in range(int(round(m.d * FPS))):
            t = i / FPS; f = np.ascontiguousarray(m.frame(t)[..., ::-1])
            for c in cards:
                if c.get('skip') or not (c['t0'] <= t <= c['t1']): continue
                u = t - c['t0']; v = c['t1'] - t
                kin = 1 + 2.6 * (min(1, u / 0.42) - 1) ** 3 + 1.6 * (min(1, u / 0.42) - 1) ** 2     # bật ra, nảy nhẹ
                kout = eout(v / 0.3) if v < 0.3 else 1.0
                k = min(kin, kout) if u >= 0.42 else kin * kout
                px, py = P_at(t, m.items[c['item']]['pf'])
                for ph in (0.0, 0.5):
                    kk = (u * 1.1 + ph) % 1.0; a2 = 0.8 * (1 - kk) * min(1, kout * 2)
                    lay = f.copy(); cv2.circle(lay, (int(px), int(py)), int(8 + 48 * kk), GOLD, 2, cv2.LINE_AA); f = cv2.addWeighted(lay, a2, f, 1 - a2, 0)
                cxF, cyF = c['BX'] + c['PW'] / 2, c['BY'] + c['PH'] / 2; kc = max(0.0, min(1.0, k)); sc = max(0.04, k)
                cx_ = px + (cxF - px) * kc; cy_ = py + (cyF - py) * kc
                w2, h2 = max(6, int(c['PW'] * sc)), max(6, int(c['PH'] * sc)); x0, y0 = int(cx_ - w2 / 2), int(cy_ - h2 / 2)
                x0 = min(max(x0, BD), W - w2 - BD); y0 = min(max(y0, BD), H - h2 - BD)
                ax = min(max(px, x0 + 20), x0 + w2 - 20); ay = y0 if py < y0 else (y0 + h2 if py > y0 + h2 else py)
                if y0 <= py <= y0 + h2: ax = x0 if px < x0 else x0 + w2
                la = min(1, kc * 1.4); lay = f.copy()
                if c.get('stem') == 'elbow': cv2.polylines(lay, [np.int32([(px, py), (x0 + 24, py), (x0 + 24, y0 + h2 if py > y0 + h2 else y0)])], False, GOLD, 3, cv2.LINE_AA)
                else: cv2.line(lay, (int(px), int(py)), (int(ax), int(ay)), GOLD, 3, cv2.LINE_AA)
                cv2.circle(lay, (int(px), int(py)), 8, (200, 240, 255), -1, cv2.LINE_AA); f = cv2.addWeighted(lay, la, f, 1 - la, 0)
                fr = c['clip'][min(len(c['clip']) - 1, int(u * FPS))]; vid = cv2.resize(fr, (w2, h2), interpolation=cv2.INTER_AREA).astype(np.float32)
                mk = cv2.resize(c['mask'], (w2, h2)).astype(np.float32)[..., None] / 255 * min(1, kc * 1.5)
                sh = np.zeros((H, W), np.float32); y1, x1 = min(H, y0 + h2 + 12), min(W, x0 + w2)
                sh[y0 + 12:y1, x0:x1] = mk[:y1 - y0 - 12, :x1 - x0, 0]; sh = cv2.GaussianBlur(sh, (0, 0), 16)
                f = (f * (1 - 0.5 * sh[..., None])).astype(np.uint8)
                roi = f[y0:y0 + h2, x0:x0 + w2].astype(np.float32); f[y0:y0 + h2, x0:x0 + w2] = (roi * (1 - mk) + vid * mk).astype(np.uint8)
                bm = np.zeros((h2 + 2 * BD, w2 + 2 * BD), np.uint8); bm[BD:BD + h2, BD:BD + w2] = cv2.resize(c['mask'], (w2, h2))
                ring = np.clip(cv2.dilate(bm, np.ones((2 * BD + 1, 2 * BD + 1), np.uint8)).astype(np.float32) - bm, 0, 255) / 255
                if u < 0.9:                                  # vệt sáng chạy viền một lần
                    yy, xx = np.mgrid[0:ring.shape[0], 0:ring.shape[1]]; pos = (xx + yy) / (ring.shape[0] + ring.shape[1])
                    ring = ring * (1 + 1.6 * np.exp(-((pos - (u - 0.35) / 0.5) / 0.07) ** 2))
                ring = np.clip(ring, 0, 2.5)[..., None] * min(1, kc * 1.5); ys, xs = y0 - BD, x0 - BD
                roi = f[ys:ys + ring.shape[0], xs:xs + ring.shape[1]].astype(np.float32)
                f[ys:ys + ring.shape[0], xs:xs + ring.shape[1]] = np.clip(roi * (1 - np.minimum(ring, 1)) + np.array(GOLD, np.float32) * ring, 0, 255).astype(np.uint8)
            p.stdin.write(f.tobytes())
        p.stdin.close(); p.wait(); print('  ✓', out, '(bản đồ + thẻ điểm đến)')

def main():
    da = sys.argv[1]; what = sys.argv[2] if len(sys.argv) > 2 else 'all'
    X = load_json(os.path.join(da, 'extras.json'), None)
    if not X: sys.exit('Chưa có DA/extras.json — xem reference/schema.md mục 9')
    if what in ('pair', 'all') and X.get('pair'): do_pair(da, X['pair'], X)
    if what in ('ranh', 'all') and X.get('ranh'): do_ranh(da, X['ranh'], X)
    if what in ('zone', 'all'):
        for z in ([X['zone']] if isinstance(X.get('zone'), dict) else X.get('zone', [])): do_zone(da, z, X)
    if what in ('cards', 'all') and X.get('cards'): do_cards(da, X)

if __name__ == '__main__':
    main()
