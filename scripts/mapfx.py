"""realcut · BẢN ĐỒ KHOẢNG CÁCH — ảnh vệ tinh + ghim BĐS + đường đi thật tới từng tiện ích + thẻ km vàng nhũ.
  python mapfx.py DA                  → DA/broll_916/<id>.mp4, đăng ký vào DA/broll/index.json
                                        (dùng trong edit.json như B-roll: {"t":…, "d":…, "src":"<id>", "move":"none"})
  python mapfx.py DA --check          → chỉ tra toạ độ + tính khoảng cách, in bảng (không dựng) — BÁO ANH XÁC NHẬN
  python mapfx.py DA --frames 21,23   → ảnh thử DA/qc/map_<id>_<giây>.jpg (giây trên video)
Cấu hình DA/map.json — reference/schema.md mục 5. Ảnh vệ tinh: Bing · đường đi: OSRM/OpenStreetMap · tra tên: Nominatim.
"""
import argparse, json, math, os, re, subprocess, sys, urllib.parse
from concurrent.futures import ThreadPoolExecutor
import numpy as np, cv2
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import Writer, load_json, save_json, die, PALETTE
import textfx as T

W, H, FPS = 1080, 1920, 30
SAFE = (0.06, 0.14, 0.94, 0.65)          # vùng chữ an toàn Reels (tỉ lệ khung)
BOX = (0.16, 0.22, 0.84, 0.58)           # vùng đặt các điểm — chừa chỗ cho thẻ
HOME_DIR = os.path.join(os.path.expanduser('~'), '.realcut'); TILES = os.path.join(HOME_DIR, 'tiles')
UA = 'realcut/1.0 (video BDS Dak Lak)'
GOLD, GOLD_HI, CREAM, INK = (246, 196, 72), (255, 236, 180), PALETTE['cream'], (24, 18, 12)

def curl(url, timeout=25):
    return subprocess.run(['curl', '-s', '--max-time', str(timeout), '-A', UA, url], capture_output=True).stdout

# ───────── toạ độ · khoảng cách ─────────
def _order(a, b):                         # → (lon, lat); Việt Nam: vĩ độ 8–24, kinh độ 102–110
    return (a, b) if 100 < a < 120 else (b, a)

def parse_at(at):
    """[lat,lon] | [lon,lat] | {"lat","lon"} | "12.68, 108.05" | link Google Maps → (lon, lat) hoặc None."""
    if isinstance(at, dict): return float(at['lon']), float(at['lat'])
    if isinstance(at, (list, tuple)) and len(at) == 2: return _order(float(at[0]), float(at[1]))
    if isinstance(at, str):
        for rx in (r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)', r'[?&](?:q|query|ll)=(-?\d+\.\d+),\s*(-?\d+\.\d+)',
                   r'@(-?\d+\.\d+),\s*(-?\d+\.\d+)', r'(-?\d{1,3}\.\d{3,})\s*,\s*(-?\d{1,3}\.\d{3,})'):
            m = re.search(rx, at)
            if m: return _order(float(m.group(1)), float(m.group(2)))
    return None

def geocode(q, cache):
    k = 'g:' + q.strip().lower()
    if k not in cache:
        js = []
        for qq in (q + ', Đắk Lắk, Việt Nam', q + ', Việt Nam'):
            try: js = json.loads(curl('https://nominatim.openstreetmap.org/search?' + urllib.parse.urlencode({'q': qq, 'format': 'json', 'limit': 1})) or b'[]')
            except Exception: js = []
            if js: break
        if not js: return None
        cache[k] = [float(js[0]['lon']), float(js[0]['lat']), js[0].get('display_name', '')[:90]]
    return cache[k]

def locate(obj, cache):
    """→ (lon, lat, nguồn)"""
    p = parse_at(obj.get('at')) if obj.get('at') is not None else None
    if p: return p[0], p[1], 'toạ độ anh đưa'
    q = obj.get('at') if isinstance(obj.get('at'), str) else obj['name']
    g = geocode(q, cache)
    if not g: die(f'Không tìm thấy "{q}" trên OpenStreetMap — xin anh toạ độ: Google Maps → nhấn giữ điểm → chép "12.68, 108.05" vào "at"')
    return g[0], g[1], f'tra tên OSM: {g[2]}'

def hav(a, b):
    R = 6371000; la1, la2 = math.radians(a[1]), math.radians(b[1]); dl = math.radians(b[0] - a[0]); dp = la2 - la1
    return 2 * R * math.asin(math.sqrt(math.sin(dp / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin(dl / 2) ** 2))

def route(a, b, cache, mode):
    """→ (toạ độ tuyến, mét, giây|None, nguồn)"""
    if mode == 'line': return [a, b], hav(a, b), None, 'đường chim bay'
    k = f'r:{a[0]:.5f},{a[1]:.5f};{b[0]:.5f},{b[1]:.5f}'
    if k not in cache:
        try:
            r = json.loads(curl(f'https://router.project-osrm.org/route/v1/driving/{a[0]},{a[1]};{b[0]},{b[1]}?overview=full&geometries=geojson'))['routes'][0]
            cache[k] = [r['geometry']['coordinates'], r['distance'], r['duration']]
        except Exception:
            cache[k] = None
    if not cache[k]: return [a, b], hav(a, b), None, 'chim bay (không lấy được đường bộ)'
    g, d, s = cache[k]; return [tuple(p) for p in g], d, s, 'đường bộ OSRM/OSM'

def fmt_km(m):
    if m < 1000: return f'{int(round(m / 50.0) * 50)} m'
    v = f'{m / 1000:.1f}'.rstrip('0').rstrip('.')
    return v.replace('.', ',') + ' km'

# ───────── ảnh vệ tinh ─────────
def world(lon, lat):                      # Web Mercator, đơn vị = cả thế giới (0..1)
    s = math.sin(math.radians(max(-85, min(85, lat))))
    return (lon + 180) / 360, 0.5 - math.log((1 + s) / (1 - s)) / (4 * math.pi)

def tiles(z, x0, y0, x1, y1):
    """ghép ảnh vệ tinh Bing ở zoom z, vùng pixel (x0,y0)–(x1,y1); cache ~/.realcut/tiles"""
    os.makedirs(TILES, exist_ok=True)
    tx = range(int(x0 // 256), int(x1 // 256) + 1); ty = range(int(y0 // 256), int(y1 // 256) + 1)
    def qk(x, y): return ''.join(str(((x >> i) & 1) | (((y >> i) & 1) << 1)) for i in range(z - 1, -1, -1))
    def get(xy):
        x, y = xy; f = os.path.join(TILES, f'{z}_{x}_{y}.jpg')
        for _ in range(2):
            if os.path.exists(f) and os.path.getsize(f) > 1000: break
            open(f, 'wb').write(curl(f'https://ecn.t{(x + y) % 4}.tiles.virtualearth.net/tiles/a{qk(x, y)}.jpeg?g=1', 20))
        return xy, f
    with ThreadPoolExecutor(12) as ex: fs = list(ex.map(get, [(x, y) for x in tx for y in ty]))
    im = Image.new('RGB', (len(tx) * 256, len(ty) * 256), (40, 44, 38)); bad = 0
    for (x, y), f in fs:
        try: im.paste(Image.open(f).convert('RGB'), ((x - tx[0]) * 256, (y - ty[0]) * 256))
        except Exception: bad += 1
    if bad: print(f'  ⚠ {bad}/{len(fs)} ô ảnh vệ tinh không tải được')
    return im.crop((int(x0 - tx[0] * 256), int(y0 - ty[0] * 256), int(x1 - tx[0] * 256), int(y1 - ty[0] * 256)))

# ───────── một bản đồ ─────────
class Map:
    def __init__(self, spec, cache, quiet=False):
        self.s = spec; self.id = spec.get('id', 'MAP1'); self.t0 = float(spec.get('t', 0)); self.d = float(spec.get('d', 7))
        mode = spec.get('dist', 'road')
        h = spec['home']; hl = locate(h, cache); self.home = (hl[0], hl[1]); self.home_name = h.get('name', '')
        self.rows = [('★ ' + self.home_name, f'{hl[1]:.5f}, {hl[0]:.5f}', '', '', hl[2])]
        self.items = []
        for n, it in enumerate(spec.get('items', [])):
            lo = locate(it, cache); p = (lo[0], lo[1])
            g, m, sec, src = route(self.home, p, cache, it.get('dist', mode))
            if it.get('km') is not None:
                txt = it['km'] if isinstance(it['km'], str) else fmt_km(float(it['km']) * 1000); ksrc = 'anh đưa'
                if not isinstance(it['km'], str) and abs(float(it['km']) * 1000 - m) > max(300, 0.25 * m):
                    print(f'  ⚠ {it["name"]}: anh ghi {it["km"]} km, {src} tính {m / 1000:.1f} km — xem lại')
            else:
                txt, ksrc = fmt_km(m), src
            mins = it.get('min')
            if mins is None and spec.get('show_min') and sec: mins = max(1, round(sec / 60))
            rel = (float(it['t']) - self.t0) if it.get('t') is not None else 1.3 + 1.5 * n
            self.items.append(dict(name=it['name'], p=p, route=g, km=txt, min=mins, rel=rel))
            self.rows.append((it['name'], f'{p[1]:.5f}, {p[0]:.5f}', f'{m / 1000:.2f} km', txt + (f' · {mins} phút' if mins else ''), f'{ksrc} · vị trí: {lo[2]}'))
        self.rings = spec.get('rings', [])
        self.note = spec.get('note') or self._note()

    def _note(self):
        srcs = {r[4].split(' · ')[0] for r in self.rows[1:]}
        if srcs == {'anh đưa'}: return 'Ảnh vệ tinh: Bing Maps'
        if any('OSRM' in s for s in srcs): return 'Ảnh vệ tinh: Bing Maps · Khoảng cách theo đường bộ (OSM)'
        return 'Ảnh vệ tinh: Bing Maps · Khoảng cách đường chim bay'

    def table(self):
        print(f'\n[{self.id}]  {self.t0:.2f}s → {self.t0 + self.d:.2f}s  ·  ghi chú: {self.note}')
        for r in self.rows:
            print(f'  {r[0][:28]:28s} {r[1]:22s} tính {r[2]:>9s}  hiện {r[3]:14s} ({r[4]})')

    # —— bố cục ——
    def layout(self):
        pts = [self.home] + [q for it in self.items for q in it['route']]
        ws = np.array([world(*p) for p in pts]); wx0, wy0 = ws.min(0); wx1, wy1 = ws.max(0)
        hx, hy = world(*self.home); lat = self.home[1]
        mpw = 40075016 * math.cos(math.radians(lat))                       # mét / 1 đơn vị thế giới (ngang)
        span = max(self.s.get('min_span_m', 900), max(self.rings or [0]) * 2000 * 1.05) / mpw
        wx0, wx1 = min(wx0, hx - span / 2), max(wx1, hx + span / 2); wy0, wy1 = min(wy0, hy - span / 2), max(wy1, hy + span / 2)
        bw, bh = (BOX[2] - BOX[0]) * W, (BOX[3] - BOX[1]) * H
        k = min(bw / (wx1 - wx0), bh / (wy1 - wy0)); ze = min(math.log2(k / 256), 18.3); k = 256 * 2 ** ze
        self.k, self.ze, self.mpp = k, ze, mpw / k
        self.cw = ((wx0 + wx1) / 2, (wy0 + wy1) / 2); self.bc = ((BOX[0] + BOX[2]) / 2 * W, (BOX[1] + BOX[3]) / 2 * H)
        self.hf = self.f(self.home)
        for it in self.items:
            it['pf'] = self.f(it['p']); it['rf'] = np.array([self.f(q) for q in it['route']], np.float32)

    def f(self, p):                       # (lon,lat) → pixel khung ở trạng thái nghỉ (s = 1)
        x, y = world(*p); return ((x - self.cw[0]) * self.k + self.bc[0], (y - self.cw[1]) * self.k + self.bc[1])

    def canvas(self):
        zt = int(min(19, math.ceil(self.ze + 0.35))); self.q = min(2.0, 2 ** (zt - self.ze))
        self.mx, self.my = 0.14 * W, 0.14 * H
        n = 256 * 2 ** zt
        X0 = (self.cw[0] + (-self.mx - self.bc[0]) / self.k) * n; Y0 = (self.cw[1] + (-self.my - self.bc[1]) / self.k) * n
        X1 = (self.cw[0] + (W + self.mx - self.bc[0]) / self.k) * n; Y1 = (self.cw[1] + (H + self.my - self.bc[1]) / self.k) * n
        print(f'  · ảnh vệ tinh zoom {zt} ({self.mpp:.1f} m/px) …', flush=True)
        im = tiles(zt, X0, Y0, X1, Y1)
        cw, ch = int((W + 2 * self.mx) * self.q), int((H + 2 * self.my) * self.q)
        c = np.asarray(im.resize((cw, ch), Image.LANCZOS), np.float32)
        g = c.mean(2, keepdims=True); c = g + (c - g) * 0.78                  # bớt rực để vàng nổi
        c = c * np.array((0.90, 0.88, 0.83), np.float32) + np.array((6, 4, 0), np.float32)
        self.cv = np.clip(c, 0, 255).astype(np.uint8)
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        r = np.sqrt(((xx - self.hf[0]) / W) ** 2 + ((yy - self.hf[1]) / H * 0.75) ** 2)
        self.vig = np.clip(1.08 - 0.75 * r ** 1.6, 0.45, 1.0)[..., None].astype(np.float32)

    def scale(self, t):
        a = T.ease_out(t / 1.5)
        return 1.32 + (1.0 - 1.32) * a - 0.03 * T.clamp01((t - 1.5) / max(self.d - 1.5, 0.1))

    # —— thẻ & bố trí nhãn ——
    def sprites(self):
        self.pin = T.pin_icon(78)
        self.hname = T.sprite(T.nfc(self.home_name.upper()), 'serif_black', T.fit_size(self.home_name.upper(), 'serif_black', 54, W * 0.7), 'gold', shadow=0.4) if self.home_name else None
        self.hsub = T.sprite(T.nfc(self.s['home'].get('sub', '').upper()), 'semibold', 24, 'cream', tracking=0.22) if self.s['home'].get('sub') else None
        for it in self.items:
            ks = T.sprite(T.nfc(it['km']), 'serif_black', 66, 'gold', shadow=0.35)
            ns = T.sprite(T.nfc(it['name']), 'semibold', T.fit_size(it['name'], 'semibold', 32, W * 0.38), 'cream')
            ms = T.sprite(T.nfc(f'≈ {it["min"]} phút'), 'medium', 26, 'cream') if it.get('min') else None
            pad = 22; w = max(ks['w'], ns['w'], ms['w'] if ms else 0) + 2 * pad; h = pad + ks['h'] + 4 + ns['h'] + (ms['h'] + 2 if ms else 0) + pad - 6
            it['card'] = dict(k=ks, n=ns, m=ms, w=int(w), h=int(h), pad=pad)
        self.title = T.sprite(T.nfc(self.s['title'].upper()), 'medium', 30, 'cream', tracking=0.3, shadow=0.5) if self.s.get('title') else None
        self.notesp = T.sprite(T.nfc(self.note), 'medium', 22, 'cream', shadow=0.5)

    def place(self):
        sx0, sy0, sx1, sy1 = SAFE[0] * W, SAFE[1] * H, SAFE[2] * W, SAFE[3] * H
        taken = []
        hx, hy = self.hf; ph = self.pin['h']
        if self.hname:
            w = max(self.hname['w'], self.hsub['w'] if self.hsub else 0) + 56; h = self.hname['h'] + (self.hsub['h'] + 6 if self.hsub else 0) + 30
            y = hy - ph - 16 - h
            if y < sy0 + (60 if self.title else 0): y = hy + 22
            x = min(max(hx - w / 2, sx0), sx1 - w); self.hrect = (x, y, w, h); taken.append(self.hrect)
        taken.append((hx - ph / 2, hy - ph, ph, ph))
        for it in self.items:
            px, py = it['pf']; taken.append((px - 16, py - 16, 32, 32))
        top = sy0 + (56 if self.title else 0); bot = 0.605 * H
        def clamp(r):
            return (min(max(r[0], sx0), sx1 - r[2]), min(max(r[1], top), bot - r[3]), r[2], r[3])
        for it in self.items:
            c = it['card']; w, h = c['w'], c['h']; px, py = it['pf']
            away = 1 if px >= hx else -1
            cands = []
            for g in (28, 70, 120):
                cands += [(g, -h - g), (-w - g, -h - g), (g, g), (-w - g, g), (g + 6, -h / 2), (-w - g - 6, -h / 2), (-w / 2, -h - g - 12), (-w / 2, g + 12)]
            best = None
            for dx, dy in cands:
                r = clamp((px + dx, py + dy, w, h))
                ov = sum(_ov(r, o) for o in taken)
                cx = r[0] + w / 2 - px
                lead = math.hypot(min(max(px, r[0]), r[0] + w) - px, min(max(py, r[1]), r[1] + h) - py)
                sc = ov * 50 + lead * 3 + (0 if cx * away > 0 else 150) + (5000 if r[0] <= px <= r[0] + w and r[1] <= py <= r[1] + h else 0)
                if best is None or sc < best[0]: best = (sc, r)
            r = best[1]; it['off'] = (r[0] - px, r[1] - py); taken.append(r)
        self.ring_lab = []
        for km in self.rings:
            rr = km * 1000 / self.mpp; lab = T.sprite(f'{km:g} km'.replace('.', ','), 'semibold', 24, 'gold_hi', shadow=0.6)
            opts = []
            for ang in (-45, -135, 45, 135, -90, 90, 0, 180):
                a_ = math.radians(ang); x = hx + rr * math.cos(a_) + 6; y = hy + rr * math.sin(a_) - lab['h']
                rect = (x, y, lab['w'], lab['h'])
                inside = sx0 <= x and x + lab['w'] <= sx1 and top <= y and y + lab['h'] <= bot
                opts.append((sum(_ov(rect, o) for o in taken) + (0 if inside else 1e7), ang, rect))
            sc, ang, rect = min(opts, key=lambda o: o[0])
            self.ring_lab.append((lab, ang, None if sc >= 1e7 else 1)); taken.append(rect)

    # —— vẽ một khung ——
    def frame(self, t):
        s = self.scale(t); hx, hy = self.hf; q = self.q
        M = np.array([[s / q, 0, hx - s * (self.mx + hx)], [0, s / q, hy - s * (self.my + hy)]], np.float32)
        img = cv2.warpAffine(self.cv, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT)
        img = (img.astype(np.float32) * self.vig).astype(np.uint8)
        P = lambda p: (hx + (p[0] - hx) * s, hy + (p[1] - hy) * s)
        # vòng bán kính
        for n, km in enumerate(self.rings):
            e = T.ease_out((t - 0.5 - 0.25 * n) / 0.6)
            if e <= 0: continue
            r = km * 1000 / self.mpp * s
            _blend(img, lambda L: _dashed_circle(L, (hx, hy), r, GOLD_HI, 2), 0.55 * e)
            lab, ang, ok = self.ring_lab[n]
            if ok: T.over(img, lab, hx + r * math.cos(math.radians(ang)) + 6, hy + r * math.sin(math.radians(ang)) - lab['h'], 0.85 * e)
        # tuyến đường
        cur = [i for i, it in enumerate(self.items) if t >= it['rel'] - 0.12]
        for i in cur:
            it = self.items[i]; p = T.ease_in_out((t - it['rel'] + 0.12) / 0.75)
            pts = np.array([P(v) for v in it['rf']], np.float32); part = _cut(pts, p)
            op = 1.0 if i == cur[-1] else 0.55
            if len(part) >= 2:
                pl = [np.round(part * 4).astype(np.int32)]
                _blend(img, lambda L: cv2.polylines(L, pl, False, INK, 15, cv2.LINE_AA, 2), 0.45 * op)
                _blend(img, lambda L: cv2.polylines(L, pl, False, GOLD, 7, cv2.LINE_AA, 2), op)
                _blend(img, lambda L: cv2.polylines(L, pl, False, (255, 247, 214), 2, cv2.LINE_AA, 2), 0.8 * op)
                if p < 1:
                    hd = tuple(int(v) for v in part[-1])
                    _blend(img, lambda L: cv2.circle(L, hd, 16, GOLD_HI, -1, cv2.LINE_AA), 0.35)
                    cv2.circle(img, hd, 8, (255, 250, 230), -1, cv2.LINE_AA)
        # ghim BĐS + vòng toả
        e0 = T.ease_out((t - 0.1) / 0.45)
        if e0 > 0:
            for ph in (0.0, 0.8):
                k = ((t + ph) % 1.6) / 1.6
                _blend(img, lambda L: cv2.circle(L, (int(hx), int(hy)), int(14 + 70 * k), GOLD_HI, 3, cv2.LINE_AA), 0.7 * (1 - k) * e0)
            cv2.circle(img, (int(hx), int(hy)), 7, GOLD, -1, cv2.LINE_AA)
            pin = self.pin; T.over(img, pin, hx - pin['w'] / 2, hy - pin['h'] * 0.97 - (1 - e0) * 60, e0)
        if self.hname:
            e = T.ease_out((t - 0.35) / 0.45)
            if e > 0:
                x, y, w, h = self.hrect; y += (1 - e) * 14
                T.glass(img, x, y, w, h, alpha=0.5, radius=int(h / 2.6), opacity=e)
                T.over(img, self.hname, x + w / 2 - self.hname['w'] / 2, y + 15, e)
                if self.hsub: T.over(img, self.hsub, x + w / 2 - self.hsub['w'] / 2, y + 15 + self.hname['h'] + 6, e)
        # điểm tiện ích + thẻ
        for i in cur:
            it = self.items[i]; tp = t - it['rel'] + 0.12 - 0.75
            pe = T.ease_out(tp / 0.25)
            if pe <= 0: continue
            px, py = P(it['pf'])
            cv2.circle(img, (int(px), int(py)), int(13 * pe), GOLD, -1, cv2.LINE_AA)
            cv2.circle(img, (int(px), int(py)), int(7 * pe), (255, 250, 235), -1, cv2.LINE_AA)
            ce = T.ease_out((tp + 0.1) / 0.35) * (1.0 if i == cur[-1] else 0.8)
            if ce <= 0: continue
            c = it['card']; x, y = px + it['off'][0], py + it['off'][1] + (1 - ce) * 12
            x = min(max(x, SAFE[0] * W), SAFE[2] * W - c['w']); y = min(max(y, SAFE[1] * H), 0.605 * H - c['h'])
            ax, ay = min(max(px, x), x + c['w']), min(max(py, y), y + c['h'])
            _blend(img, lambda L: cv2.line(L, (int(px), int(py)), (int(ax), int(ay)), GOLD_HI, 2, cv2.LINE_AA), 0.8 * ce)
            T.glass(img, x, y, c['w'], c['h'], alpha=0.55, radius=18, opacity=ce)
            T.hline(img, x + c['pad'], y + 10, 46, 3, 'gold', ce)
            yy = y + c['pad'] - 4
            T.over(img, c['k'], x + c['pad'] - c['k'].get('xoff', 0) * 0, yy, ce); yy += c['k']['h'] + 4
            T.over(img, c['n'], x + c['pad'], yy, ce); yy += c['n']['h'] + 2
            if c['m']: T.over(img, c['m'], x + c['pad'], yy, ce * 0.9)
        if self.title:
            e = T.ease_out((t - 0.2) / 0.4)
            T.over(img, self.title, W / 2 - self.title['w'] / 2, 0.15 * H - self.title['h'] / 2, e)
            T.hline(img, W / 2 - 40, 0.15 * H + self.title['h'] / 2 + 8, 80 * e, 3, 'gold', e)
        T.over(img, self.notesp, W / 2 - self.notesp['w'] / 2, 0.632 * H - self.notesp['h'], 0.6 * T.ease_out((t - 0.6) / 0.5))
        return img

def _ov(a, b):
    return max(0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0])) * max(0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))

def _blend(img, draw, op):
    if op <= 0.01: return
    L = img.copy(); draw(L); cv2.addWeighted(L, op, img, 1 - op, 0, dst=img)

def _cut(pts, p):
    if p >= 1 or len(pts) < 2: return pts
    seg = np.hypot(*(pts[1:] - pts[:-1]).T); cum = np.concatenate([[0], np.cumsum(seg)]); L = cum[-1] * p
    j = int(np.searchsorted(cum, L)) ; j = max(1, min(j, len(pts) - 1))
    f = (L - cum[j - 1]) / max(seg[j - 1], 1e-6); end = pts[j - 1] + (pts[j] - pts[j - 1]) * f
    return np.vstack([pts[:j], end[None]])

def _dashed_circle(L, c, r, col, th):
    n = max(24, int(r / 9))
    for k in range(0, n, 2):
        a0, a1 = 360 * k / n, 360 * (k + 1) / n
        cv2.ellipse(L, (int(c[0] * 4), int(c[1] * 4)), (int(r * 4), int(r * 4)), 0, a0, a1, col, th, cv2.LINE_AA, 2)

def register(da, mid, path, d):
    p = os.path.join(da, 'broll', 'index.json'); os.makedirs(os.path.dirname(p), exist_ok=True)
    j = load_json(p, {'items': []}); j['items'] = [x for x in j.get('items', []) if x.get('id') != mid]
    j['items'].append(dict(id=mid, file=os.path.abspath(path), w=W, h=H, dur=round(d, 2), kind='map')); save_json(p, j)

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('da'); ap.add_argument('--check', action='store_true'); ap.add_argument('--frames')
    ap.add_argument('--only'); a = ap.parse_args()
    cfg = load_json(os.path.join(a.da, 'map.json'))
    if not cfg: die('Chưa có DA/map.json — xem reference/schema.md mục 5')
    cp = os.path.join(a.da, 'geo_cache.json'); cache = load_json(cp, {})
    maps = [m for m in cfg.get('maps', []) if not a.only or m.get('id') == a.only]
    for spec in maps:
        m = Map(spec, cache); save_json(cp, cache); m.table()
        if a.check: continue
        m.layout(); m.canvas(); m.sprites(); m.place()
        if a.frames:
            qc = os.path.join(a.da, 'qc'); os.makedirs(qc, exist_ok=True)
            for tv in [float(x) for x in a.frames.split(',')]:
                if not (m.t0 <= tv <= m.t0 + m.d): continue
                out = os.path.join(qc, f'map_{m.id}_{tv:g}.jpg'); cv2.imwrite(out, m.frame(tv - m.t0)[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 88]); print('  ✓', out)
            continue
        od = os.path.join(a.da, 'broll_916'); os.makedirs(od, exist_ok=True); out = os.path.join(od, f'{m.id}.mp4')
        wr = Writer(out, W, H, FPS, crf=16, preset='medium'); n = int(round(m.d * FPS))
        for i in range(n): wr.write(np.ascontiguousarray(m.frame(i / FPS)))
        wr.close(); register(a.da, m.id, out, m.d)
        print(f'  ✓ {out} · {m.d:.1f}s → edit.json: {{"t": {m.t0}, "d": {m.d}, "src": "{m.id}", "move": "none"}}')
    if a.check: print('\n→ Báo anh bảng trên (vị trí + khoảng cách) để xác nhận trước khi dựng.')

if __name__ == '__main__':
    main()
