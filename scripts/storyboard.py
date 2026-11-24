# realcut storyboard — bảng phân cảnh để anh Vũ sửa TRƯỚC khi dựng (anh yêu cầu 24/11/2026)
#   realcut.py storyboard DA                 → DA/storyboard.xlsx (mỗi cảnh 1 dòng + ảnh minh hoạ) + DA/storyboard.jpg (xem nhanh)
#   realcut.py storyboard DA --read FILE     → so bản anh sửa với bản gốc, in các ô đã đổi + cột "ANH SỬA" để Claude cập nhật json
# Nguồn: lời (words_cut.json) · nền (edit.json broll) · chữ/âm (ads.json) · bản đồ (map.json) · đồ hoạ (extras.json)
import sys, os, json, subprocess
import numpy as np, cv2
from PIL import Image, ImageDraw
from common import load_json, save_json
da = sys.argv[1]
J = lambda n, d=None: load_json(os.path.join(da, n), d)
COLS = ['CẢNH', 'GIÂY', 'LỜI ANH NÓI', 'HÌNH NỀN', 'CHỮ TRÊN HÌNH', 'ĐỒ HOẠ / HIỆU ỨNG', 'ÂM THANH', 'ẢNH', 'ANH SỬA']

def read_back(path):
    import openpyxl
    snap = J('storyboard.json', {}).get('rows', [])
    ws = openpyxl.load_workbook(path).active; rows = list(ws.iter_rows(min_row=2, values_only=True)); n = 0
    for i, r in enumerate(rows):
        r = [('' if v is None else str(v)) for v in r]
        if i >= len(snap) and not r[0].strip(): continue           # dòng ghi chú nhạc cuối bảng
        o = snap[i] if i < len(snap) else [''] * len(COLS)
        for j, col in enumerate(COLS):
            if col == 'ẢNH' or j >= len(r): continue
            if r[j].strip() != (o[j] if j < len(o) else '').strip():
                print(f'Cảnh {r[0] or i + 1} · {col}:\n    trước: {(o[j] if j < len(o) else "") or "—"}\n    anh sửa: {r[j] or "(xoá)"}'); n += 1
    print(f'→ {n} ô đã sửa' if n else '→ anh không sửa ô nào')

def label_src(b, maps, X):
    s = str(b.get('src', ''))
    for m in maps:
        if s == m['id']:
            return f"Bản đồ vệ tinh {m['id']}: ghim lô → " + ' → '.join(f"{it['name']} ({it.get('km', '')})" for it in m.get('items', []))
    base = os.path.splitext(os.path.basename(s))[0]
    if X.get('ranh') and base == X['ranh'].get('id'): return f"Ranh giới xã {X['ranh'].get('xa')} (line sáng) → zoom vào lô"
    zs = X.get('zone'); zs = [zs] if isinstance(zs, dict) else (zs or [])
    for z in zs:
        if base == z.get('id'): return 'Khu quy hoạch trên vệ tinh: line chạy ranh → quét lộ phối cảnh'
    if X.get('pair') and base == X['pair'].get('id'): return 'Ghép 2 hình: ' + ' + '.join(X['pair'].get('labels', ['toàn cảnh', 'sơ đồ phân lô'])).lower()
    return f'B-roll {s}' + (f" (từ giây {b['in']})" if b.get('in') else '')

def thumb(src, t, idx):
    if not os.path.exists(src): return None
    out = os.path.join(da, 'qc', f'sb_{idx:02d}.jpg'); os.makedirs(os.path.dirname(out), exist_ok=True)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{max(0, t):.2f}', '-i', src, '-frames:v', '1', '-vf', 'scale=135:240', out])
    return out if os.path.exists(out) else None

def build():
    words = J('words_cut.json', {}).get('words', []); dur = J('words_cut.json', {}).get('dur') or (words[-1]['e'] if words else 0)
    E = J('edit.json', {}); A = J('ads.json', {}); M = J('map.json', {}).get('maps', []); X = J('extras.json', {})
    idx = {i['id']: i['file'] for i in J('broll/index.json', {}).get('items', [])}
    br = sorted(E.get('broll', []), key=lambda b: b['t'])
    cuts = [0.0]; segs = []
    t = 0.0
    for b in br:                                             # chen đoạn mặt anh Vũ vào giữa các B-roll
        if b['t'] - t > 0.05: segs.append((t, b['t'], None))
        segs.append((b['t'], b['t'] + b['d'], b)); t = b['t'] + b['d']
    if dur - t > 0.05: segs.append((t, dur, None))
    rows, thumbs = [], []
    for n, (a, b_, bb) in enumerate(segs, 1):
        said = ' '.join(w['w'] for w in words if a - 0.05 <= w['s'] < b_ - 0.05)
        bg = 'Mặt anh Vũ nói' if bb is None else label_src(bb, M, X)
        if bb is None:
            z = [f"zoom {x.get('type', 'đẩy chậm')}" for x in E.get('aroll_zoom', []) if a <= x['t'] < b_]
            if z: bg += ' · ' + ', '.join(sorted(set(z)))
        txt = []
        h = A.get('hook')
        if h and a <= h['price_t'] < b_: txt.append(f"MÓC GIÁ: {h.get('tag', '')} {h['price']} (số chạy từ {h['price_t']}s, chốt {h['price_t'] + float(h.get('count', 0)):.2f}s)")
        for k in A.get('keywords', []):
            if a <= k['t0'] < b_:
                st = 'chữ nhỏ bạch kim' if k.get('small') else 'chữ lớn vàng'
                txt.append(f"{k['t0']:.1f}s {k['main']}" + (f" / {k['sub']}" if k.get('sub') else '') + f" [{st}{', ' + k['anim'] if k.get('anim') else ''}{', zigzag' if k.get('stack') else ''}]")
        for p in A.get('plot', []):
            if a <= p['t0'] < b_: txt.append(f"{p['t0']:.1f}s đồ hoạ lô {p['w']}×{p['l']}")
        hc = A.get('hotline_card')
        if hc and a <= hc['t0'] < b_: txt.append(f"{hc['t0']:.1f}s thẻ hotline {hc.get('number', '')}")
        fx = []
        for tt, kind in A.get('transitions', []):
            if abs(tt - a) < 0.06: fx.append(f'chuyển cảnh {kind}')
        if bb is not None:
            sid = str(bb.get('src', ''))
            for m in M:
                if sid == m['id']:
                    for c in X.get('cards', {}).get(m['id'], []):
                        it = m['items'][c['item']]; fx.append(f"thẻ {'ảnh' if str(c['src']).lower().endswith(('jpg', 'jpeg', 'png')) else 'video'} {os.path.basename(c['src'])} ở {it['name']}")
                    for t0, t1 in m['home'].get('thumb_t', []): fx.append(f"sơ đồ phân lô bung từ ghim {bb['t'] + t0:.1f}–{bb['t'] + t1:.1f}s")
        snd = []
        for k in A.get('keywords', []):
            if k.get('sfx') and a <= k.get('sfx_t', k['t0']) < b_: snd.append(f"{k.get('sfx_t', k['t0']):.1f}s {k['sfx']}")
        for s in A.get('audio', {}).get('sfx', []):
            if a <= s['t'] < b_: snd.append(f"{s['t']:.1f}s {os.path.splitext(os.path.basename(str(s['file'])))[0]}")
        if h and h.get('count') and a <= h['price_t'] < b_: snd.append(f"{h['price_t'] + float(h['count']):.1f}s tính tiền (giá)")
        for tt, kind in A.get('transitions', []):
            if abs(tt - a) < 0.06: snd.append(f'{tt:.1f}s whoosh')
        src = os.path.join(da, 'cut.mp4') if bb is None else (idx.get(bb['src']) or (bb['src'] if os.path.isabs(str(bb['src'])) else os.path.join(da, str(bb['src']))))
        tin = (a + b_) / 2 if bb is None else bb.get('in', 0) + (b_ - a) / 2 * bb.get('speed', 1.0)
        thumbs.append(thumb(src, tin, n))
        rows.append([str(n), f'{a:.1f}–{b_:.1f}', said, bg, '\n'.join(txt), '\n'.join(fx), '\n'.join(snd), '', ''])
    am = A.get('audio', {}).get('music'); note = f"Nhạc nền: {os.path.basename(am) if am else 'Life is a Dream (mặc định)'} · giọng −14 LUFS, nhạc ~15 dB dưới giọng"
    return rows, thumbs, note

def write(rows, thumbs, note):
    import openpyxl
    from openpyxl.drawing.image import Image as XImg
    from openpyxl.styles import Alignment, Font, PatternFill, Border, Side
    wb = openpyxl.Workbook(); ws = wb.active; ws.title = 'Storyboard'
    ws.append(COLS)
    for r in rows: ws.append(r)
    ws.append([]); ws.append(['', '', note])
    widths = [7, 11, 42, 34, 40, 34, 26, 20, 34]
    for i, w in enumerate(widths): ws.column_dimensions[chr(65 + i)].width = w
    hd = PatternFill('solid', fgColor='2B2B2B'); thin = Side(style='thin', color='BBBBBB')
    for c in ws[1]: c.font = Font(bold=True, color='F2C46B'); c.fill = hd; c.alignment = Alignment(horizontal='center', vertical='center')
    for i, r in enumerate(rows, start=2):
        ws.row_dimensions[i].height = 186
        for c in ws[i]: c.alignment = Alignment(wrap_text=True, vertical='top'); c.border = Border(top=thin, bottom=thin, left=thin, right=thin)
        ws.cell(i, 9).fill = PatternFill('solid', fgColor='FFF4D6')
        if thumbs[i - 2]:
            im = XImg(thumbs[i - 2]); im.width, im.height = 135, 240; ws.add_image(im, f'H{i}')
    ws.freeze_panes = 'C2'
    out = os.path.join(da, 'storyboard.xlsx'); wb.save(out)
    save_json(os.path.join(da, 'storyboard.json'), {'rows': rows})
    # ảnh xem nhanh: lưới khung + giây + nền
    from PIL import ImageFont
    fdir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'fonts')
    F1 = ImageFont.truetype(os.path.join(fdir, 'BeVietnamPro-Bold.ttf'), 13); F2 = ImageFont.truetype(os.path.join(fdir, 'BeVietnamPro-Medium.ttf'), 11)
    tiles = []
    for r, th in zip(rows, thumbs):
        im = Image.open(th).convert('RGB') if th else Image.new('RGB', (135, 240), (40, 40, 40))
        cv = Image.new('RGB', (135, 290), (24, 24, 24)); cv.paste(im, (0, 0)); d = ImageDraw.Draw(cv)
        d.text((4, 243), f"{r[0]} · {r[1]}s", fill=(242, 196, 107), font=F1)
        bgt = r[3].split(' · ')[0].split(':')[0]; d.text((4, 263), bgt[:22] + ('…' if len(bgt) > 22 else ''), fill=(225, 225, 225), font=F2); tiles.append(cv)
    cols = 8; g = Image.new('RGB', (135 * cols, 290 * ((len(tiles) + cols - 1) // cols)), (0, 0, 0))
    for k, t in enumerate(tiles): g.paste(t, ((k % cols) * 135, (k // cols) * 290))
    g.save(os.path.join(da, 'storyboard.jpg'), quality=88)
    print(f'✓ {out} · {len(rows)} cảnh · xem nhanh: {os.path.join(da, "storyboard.jpg")}')
    print('→ gửi anh file xlsx: sửa thẳng các ô hoặc ghi vào cột ANH SỬA, gửi lại → storyboard DA --read <file>')

if __name__ == '__main__':
    if '--read' in sys.argv: read_back(sys.argv[sys.argv.index('--read') + 1])
    else: write(*build())
