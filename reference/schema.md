# Cấu trúc file dự án (mọi mốc = GIÂY của `cut.mp4`, tức sau khi đã 1.1× và cắt lặng)

Tra mốc bằng `realcut.py phrases DA`. Ví dụ đầy đủ đã duyệt: `templates/ads_example.json`, `templates/edit_example.json` (ERA City) — chỉ mở khi cần xem một khoá cụ thể.

## 0 · Cách viết nhanh (đi lần lượt theo lời anh)
1. Câu nói giá → `hook` (có giá so sánh thì `strike`, không có thì bỏ; `tag`/`specs` theo lời, vd "GIÁ/M²", diện tích, số tầng) · tên dự án/đường/khu → `wordmark` hoặc keyword `big: true` · ý anh nhấn → `keywords` · liệt kê → `chips` (mỗi viên đúng lúc được nói) · con số → `stats`/`cards` · ưu đãi % → `offer` · câu đắt → `quote`. Không dùng hiệu ứng nào mà lời không có chỗ cho nó.
2. `pos`: cảnh người nói → `top`; B-roll/blur-fit → `low`; cảnh có thể sáng → `auto`.
3. `transitions` ở chỗ lời chuyển ý lớn; `whip` cùng hướng chuyển động máy.
4. `road`: xem khung ở `ref_t`, chấm 2 điểm trên tim đường → `p1`, `p2`. Một nhãn đường/video; nhiều đường → hỏi anh. Chưa có hiệu ứng vẽ ranh lô đất → anh cần thì báo là tính năng phải bổ sung vào script.
5. `end`: nền là cảnh đẹp nhất, nội dung theo câu kết (`end_hold` trong edit.json).
6. `audio.drop.video` = giây câu anh nhấn mạnh nhất (thường `hook.price_t`).
7. B-roll: `in + d×speed` ≤ độ dài clip, quá là đứng hình không báo.

## 1 · `DA/edit.json` — tầng A (nền)
```json
{
 "ratio": "9:16",
 "grade": {"preset": "neutral", "strength": 1.0, "sat": 1.03},   // neutral | warm | golden
 "end_hold": 3.0,                       // giữ thêm sau lời cuối (giây) cho khung kết
 "broll": [                             // mỗi cảnh 1–2.5 s, cắt cứng
   {"t": 14.49, "d": 3.74, "src": "B02", // id trong DA/broll/index.json hoặc đường dẫn file
    "in": 0.3,                          // giây bắt đầu trong clip; nhớ in + d×speed ≤ độ dài clip
    "speed": 1.6,                       // flycam chậm → 1.3–1.6; cảnh người → 1.0
    "move": "push",                     // push | pull | left | right | up | down | rise | none
    "xf": 0}                            // hoà cảnh (s); 0 = cắt cứng (mặc định)
 ],
 "aroll_zoom": [                        // nhịp trên mặt người nói (tâm = đầu)
   {"t": 8.54, "d": 1.3, "from": 1.0, "to": 1.05},      // đẩy chậm
   {"t": 9.86, "d": 2.0, "type": "punch", "scale": 1.14} // cắt cận tức thì cho câu nhấn
 ]
}
```

## 2 · `DA/ads.json` — tầng B (chữ & hiệu ứng) + tầng C (âm thanh)
Mục nào không cần thì bỏ hẳn khoá đó.

```json
{
 "brand": {"name": "ERA City", "hotline": "0949.435.499"},
 "display_font": "lpv",                // font chữ nhấn — mặc định LPV Display (font riêng anh Vũ, duy nhất); chỉ đổi khi anh yêu cầu
 "watermark": {"text": "LE PHONG VU", "font": "business", "size": 37, "tracking": 0.32, "opacity": 0.50},  // bỏ trống = mặc định này · false = tắt · luôn là lớp chìm dưới cùng
 "hotline_card": {"t0": 46.46, "t1": 48.67, "number": "0949.435.499", "x": 0.80, "y": 0.565},   // khung HOTLINE nhỏ (nhãn trắng + số vàng nhũ) đặt khoảng trống cạnh người; thay khung kết
 "darken": 0.52,                       // mức tối khung khi chữ hiện trên nền sáng

 "hook": {                             // MÓC GIÁ 0–7 s: giá so sánh bị gạch → giá chính vàng nhũ cực to
   "strike": [["8 TỶ", 0.11, 0.93, 0.180], ["9 TỶ", 1.18, 1.69, 0.236]],  // [chữ, hiện, gạch, y]
   "price": "7,5 TỶ", "price_t": 3.38, "price_size": 250, "price_y": 0.312,
   "count": 0.9,                       // tuỳ chọn: số chạy lên 0.9 s rồi chốt + chớp vàng + tiếng đếm (thay tiếng hit)
   "count": 2.14,                      // giá chạy số từ price_t (đầu câu "với mức giá…") tới hết chữ đơn vị; chốt = to lên rồi hạ ("pop": 0.14); "flash": true mới có chớp sáng; "dim": 0 mặc định (mở đầu sáng)
   "behind_until": 5.13,               // trước mốc này giá nằm SAU người nói (cần matte); sau đó nằm trên hình
   "out": 7.0,                         // cả khối rời đi
   "tag": "GIÁ FULL", "tag_t": 4.14, "tag_y": 0.352,
   "specs": [["Nhà phố", 5.11], ["ngang 6m", 5.41], ["cao 4 tầng", 6.59]], "specs_y": 0.600
 },
 "wordmark": {"t0": 7.36, "t1": 8.56, "text": "ERA City", "label": "DỰ ÁN"},   // tên dự án trên cảnh phối cảnh

 "keywords": [                         // TỪ KHOÁ VÀNG NHŨ — 1 ý đắt = 1 mục
   {"t0": 8.55, "t1": 9.87, "main": "ƯU ĐÃI", "sub": "cực kỳ hấp dẫn", "pos": "top"},
   {"t0": 14.09, "t1": 14.49, "main": "ERA City", "pos": "top", "big": true},
   {"t0": 22.74, "t1": 23.91, "main": "BẬC NHẤT", "sub": "Tây Nguyên", "pos": "low", "size": 150, "sub_size": 78},
   {"t0": 23.96, "t1": 26.80, "main": "DÒNG NGƯỜI", "sub": "DÒNG TIỀN", "layout": "stack3"},
   {"t0": 50.32, "t1": 51.35, "main": "THANH TOÁN", "sub": "linh hoạt", "pos": "auto"}
 ],
 //  pos  top  = trên đầu người nói — TỰ đặt ngay trên đỉnh đầu (head.json) và tự thu nhỏ nếu chạm mép trên
 //       low  = dải dưới vùng an toàn (0.56–0.65 H) — dùng trên B-roll / dải mờ blur-fit
 //       auto = tự nhận nền: sáng → chữ lên 0.42 H + làm tối cả khung; tối → như low
 //  dim: 0.28 = tối nhẹ cả khung khi chữ "top" nằm trên trời sáng · sub_color (từng mục hoặc khoá gốc "sub_color") = màu dòng phụ, mặc định "cream" — chỉ chữ lớn mới vàng nhũ ("gold" để dòng phụ cũng vàng)
 //  big: true = tên dự án cực to (≤ 215 px) · layout "stack3" = 3 dòng: main / & / sub cùng cỡ
 //  ghi đè tuỳ chọn: size, sub_size, y (baseline dòng chính, tỉ lệ H), y_sub

 "quote": {"t0": 29.67, "t1": 31.85, "t2": 30.36, "l1": "Dòng người đi qua,", "l2": "dòng tiền ở lại"},
 "offer": {"t0": 9.86, "t1": 14.03, "pre": "Lên đến", "value": 18, "unit": "%",
           "label": "DÀNH CHO KHÁCH HÀNG", "sub": "Booking đợt đầu", "y": 0.263, "scale": 1.28},
 "chips": [                            // thẻ kính + vạch vàng; mỗi viên hiện đúng lúc được nói
   {"t": 34.14, "d": 3.24, "items": [{"text": "Cà phê", "t": 34.66}, {"text": "Showroom", "t": 35.42}]},
   {"t": 45.52, "d": 4.8, "numbered": true, "items": [{"text": "Tự kinh doanh", "t": 46.21}]}
 ],
 "stats": {"t0": 19.48, "t1": 22.69, "items": [["~1,2 ha", "DIỆN TÍCH ĐẤT"], ["1 hầm · 7 tầng", "QUY MÔ"]]},
 "plot": [                             // ĐỒ HOẠ LÔ ĐẤT ngang × dài (đất nền): viền vàng chạy quanh ranh (kèm tiếng ranh như vucut), mép sáng + số đúng lúc nói
   {"t0": 10.90, "t1": 12.55, "w": 10, "l": 15, "x": 0.5, "y": 0.37,   // y = mép mặt tiền (tỉ lệ H); đặt vào khoảng trống, không che người
    "scale": 38, "hl": [["w", 10.92], ["l", 11.46]], "front": "Mặt tiền", "inside": "FULL THỔ CƯ", "inside_t": 12.05,
    "l_side": "right", "dim": 0.2, "draw": 0.8}                   // không trùng thời gian với keyword/móc giá (chừa 0.3 s mờ dần)
 ],
 "road": {                             // nhãn đường chạy dọc con đường trên flycam, bám chuyển động
   "t0": 15.0, "t1": 16.96, "ref_t": 15.9,          // ref_t = khung tham chiếu để chấm p1, p2
   "p1": [328, 466], "p2": [928, 652], "at": 0.5,   // 2 điểm trên TIM ĐƯỜNG (px 1080×1920) tại ref_t; at = vị trí nhãn
   "title": "Quốc lộ 14", "sub": "MẶT TIỀN ĐƯỜNG NGUYỄN CHÍ THANH"
 },
 "cards": [                            // thẻ thông tin
   {"t": 14.49, "d": 2.47, "type": "label", "y": 0.152, "text": "Vị trí"},          // nhãn chương góc trên
   {"t": 26.80, "d": 2.8, "type": "stat", "value": "152", "unit": "căn", "label": "nhà phố thương mại", "size": 0.23, "y": 0.585},
   {"t": 31.88, "d": 2.2, "type": "spec", "items": [["Mặt tiền", "6 m"]], "y": 0.562, "stagger": 0.85},
   {"t": 52.42, "d": 1.3, "type": "chapter", "num": "01", "text": "Vay ngân hàng", "y": 0.33},
   {"t": 52.51, "d": 7.9, "type": "source", "text": "Theo CSBH của CĐT", "y": 0.185, "align": "label", "size": 0.028, "font": "medium_italic"}
 ],
 "transitions": [[5.13, "zoom"], [26.80, "whip"]],   // CHỈ ở điểm chuyển chương; whip cùng hướng chuyển động
 "leaks": [[3.33, 0.62, 0.95, 1, 0.30]],            // [t0, dài, độ sáng, hướng ±1, y] — bỏ trống = tự đặt theo transitions
 "end": {"t": 65.80, "bg": {"src": "broll_916/pho_hoanghon_916.mp4", "in": 2.0},
         "title": "ERA City", "lines": ["LIÊN MINH …", "Đơn vị phân phối chính thức F1"],
         "price": "7,5 TỶ", "price_tag": "GIÁ FULL", "cta": "Nhận bảng giá & ưu đãi đợt đầu", "hotline": "0949.435.499"},

 "audio": {
   "music": "music/nhac.mp3",          // BỎ TRỐNG = nhạc mặc định anh Vũ duyệt "Life is a Dream" (Mixkit 837, tự tải, drop tự đặt lúc chốt giá, pre_drop_gain 2.0) · false = không nhạc
   "drop": {"track": 15.84, "video": 3.38},   // giây drop trong bài → giây cần drop trong video (thường = price_t)
   "music_gain": 0.545, "lufs": -13.7, "voice_ratio": 2.0,   // mặc định (anh Vũ chốt 22/11 theo video QC mẫu, đo bằng demucs): giọng ≈ −13.8 LUFS, nhạc + hiệu ứng ≈ −27.5 LUFS · "pre_drop_gain": 2.5 = nâng đoạn dạo trước drop
  
   "sfx_auto": true,  "sfx_db": {"whoosh": -24, "hit": -17, "count": -17, "out": -27}, "ranh_db": -26, "sfx_gain_db": 15,   // mức từng loại + sfx_gain_db cộng đồng loạt (mặc định +15 dB → hiệu ứng cùng mức nhạc nền); chỉ ghi khi cần đổi                   // whoosh ở transitions, hit ở giá + khung kết, shimmer ở offer (thưa ≥ 2.5 s)
   "sfx_lib": {"whoosh": "", "hit": "", "shimmer": ""},   // file riêng; trống → tự tổng hợp (không bản quyền)
   "sfx": [{"file": "sfx/tick.mp3", "t": 12.3, "db": -14}]
 }
}
```

## 3 · Thứ tự vẽ mỗi khung (để hiểu chữ nào nằm trên)
nền → watermark (chìm dưới cùng) → thẻ (label/spec/stat/chapter/source) → móc giá (lớp sau người qua matte) → wordmark → làm tối nền sáng → từ khoá → ưu đãi → chips → câu trích → dãy số liệu → nhãn đường → chuyển cảnh → khung kết → vệt sáng.

## 4 · File sinh ra trong DA
`words.json`, `words_cut.json`, `cut.mp4`, `segments.json` (prep) · `matte.mp4`, `head.json` (prep) · `broll_916/`, `broll/index.json`, `broll/sheet_*.jpg` (broll) · `broll_916/MAP*.mp4`, `geo_cache.json` (map) · `base.mp4` → `fx.mp4` → `final.mp4` · `qc/` (ảnh thử, bảng ảnh, qc_report.txt, qc_flags.jpg).

## 5 · `DA/map.json` — bản đồ khoảng cách (lệnh `map`)
Dùng khi lời anh nói vị trí / khoảng cách tới tiện ích. Dựng thành clip B-roll 9:16: vệ tinh, ghim vàng BĐS, đường đi thật chạy tới từng tiện ích đúng lúc được nhắc, thẻ km vàng nhũ.
```json
{"maps": [{
  "id": "MAP1", "t": 20.0, "d": 8.0,            // t = giây trên video (cut.mp4) bản đồ bắt đầu; d = dài
  "title": "Kết nối tiện ích",                   // tuỳ chọn: nhãn chương trên cùng
  "home": {"name": "", "label": "Vị trí", "at": "12.6680, 108.0380"},   // anh Vũ duyệt: không thẻ tên, chỉ chữ nhỏ "Vị trí" cạnh ghim
  "zoom": 3.0,                                   // camera zoom gần lô rồi chạy theo đầu tuyến đường
  "items": [                                     // thứ tự & giây theo lời anh
    {"name": "Chợ Buôn Ma Thuột", "t": 21.3, "at": "12.68, 108.04"},   // at bỏ trống → tra tên OSM (hay nhầm, phải soát)
    {"name": "Sân bay BMT", "t": 25.8, "km": 9}                         // km anh đưa → hiện đúng số anh đưa
  ],
  "dist": "road",                                // road = đường bộ OSRM (mặc định) | line = chim bay (ghi rõ trên hình)
  "show_min": false,                             // true = thêm "≈ N phút" (thời gian OSRM tính cho ô tô — chỉ bật khi anh muốn)
  "zoom": 3.0,                                   // camera zoom gần lô đất, bám đầu tuyến đường đang chạy, cuối lùi ra toàn cảnh
  "rings": [1, 3],                               // tuỳ chọn: vòng bán kính km quanh BĐS
  "note": null                                   // dòng nguồn dưới đáy; null = tự ghi (Bing · OSM)
}]}
```
- `at` nhận: `"12.68, 108.05"` (Google Maps: nhấn giữ điểm → chép), link Google Maps, `[lat, lon]`, `{"lat","lon"}`.
- **Luôn chạy `map DA --check` trước**, đưa anh bảng vị trí + km để xác nhận (tra tên OSM hay ra nhầm nơi; km tính lệch km anh ghi > 25 % → script cảnh báo). Anh sửa → điền `at`/`km`.
- `map DA --frames 21,26` xem ảnh thử → `map DA` dựng → thêm vào edit.json `{"t": 20.0, "d": 8.0, "src": "MAP1", "move": "none"}`. Chạy `map` **sau** `broll` (broll ghi lại index.json).
- Thẻ tự né nhau, nằm trong vùng an toàn; trong lúc bản đồ hiện, không đặt keyword/thẻ của ads.json đè lên (chỉ watermark).
- `map` ghi `broll_916/<id>_sfx.json` → `mix` tự thêm tiếng vệt đường chạy + "ting" khi thẻ km bật + tiếng lùi toàn cảnh (tắt: `audio.map_sfx: false`). Thẻ BĐS ẩn khi camera zoom theo tuyến, hiện lại ở toàn cảnh.
- Mỗi tiện ích ~1.3–1.5 s là đọc kịp; nhiều hơn 5–6 tiện ích → tách 2 bản đồ.

## 6 · Bộ chữ (mặc định từ 21/11/2026 — anh Vũ chốt ở ERA City tiến độ v22)
Chỉ **2 kiểu chữ** cho cả video. Bỏ trống các khoá dưới là đúng (script tự đặt); `"style": "classic"` = quay về vàng nhũ cũ.
- **Chữ lớn**: LPV Display, `big_material: "gold_brushed"` (vàng xước, mặt kim loại + mép vát + độ dày khối) — từ khoá, số chương, số trên thẻ số, số hotline.
- **Chữ nhỏ**: Be Vietnam Bold IN HOA giãn chữ, `sub_material: "platinum_brushed"` (bạch kim xước có khối) — dòng phụ từ khoá, tên chương, đơn vị ("CĂN"), nhãn thẻ số.
- Không bóng, không dải tối sau chữ (`text_shadow: false`, `kw_scrim: 0`); chữ rộng tối đa 72 % khung (`kw_max_w`).
- Chữ trên B-roll nằm **dải trên** vùng an toàn, cách mép: chữ thường `y` 0.25, chữ cấp 1 (to nhất) 0.265, thẻ chương 0.30, thẻ số 0.29, hotline 0.20. Chữ trên đầu người nói vẫn `pos: top`.
- Cấp chữ: cấp 1 (3–5 ý đắt nhất) `size` 150, `sub_size` 64 · cấp 2 `size` 112, `sub_size` 56. Không quá ~20 chữ/70 s.
- Thẻ chương làm tối nền (`dim` 0.55 mặc định); thẻ số không tối.
- Liệt kê nhấn mạnh (vd NHÌN THẤY / CẢM NHẬN / TRẢI NGHIỆM): từng keyword `stack: true` + `x`, `y` riêng xếp **zigzag**, `size` 80, `pop` 0.2 (chữ to lên rồi hạ khi xuất hiện).
- Khoá khác có sẵn: `x` (tâm ngang), `pop`, `y_sub`, `strike` (giây gạch ngang chữ lớn bằng vạch vàng — vd móc "KHÔNG PHẢI giá 1 căn nhà phố") (dòng phụ nằm trên chữ lớn). Chỉ còn 2 chất liệu đã chốt (`gold_brushed`, `platinum_brushed`) — các chất liệu thử nghiệm khác đã gỡ.
- Mẫu đầy đủ: `templates/tiendo_ads_example.json`.
