# Mẫu brief realcut — anh Vũ gửi kèm video (1 tin nhắn, dòng nào không có thì bỏ)

```
BRIEF
Loại: đất nền / nhà phố / dự án
Vị trí: 12.683386, 108.162892 · đường/khu vực: ……… (viết đúng chính tả, vd Ea Knuếc)
Giá: 630 triệu
Kích thước: ngang 10 × dài 15 · thổ cư: full · hướng: …… · lộ giới: 5 m
Pháp lý: sổ riêng / sổ hồng / ……
Tiện ích (tên · toạ độ · km muốn hiện):
- Nút giao cao tốc Khánh Hòa – BMT · 12.666016, 108.155370 · 2 km
- Vòng xoay QL26 · 12.700572, 108.165897 · 2 km
Tên riêng dễ nghe nhầm: ……
Hotline: (bỏ trống = 0949.435.499)
Ghi chú: chỗ muốn nhấn / cảnh muốn bỏ / nhạc riêng ……
```

Cách dùng (cho người dựng):
- Brief là nguồn chính cho mọi con số lên hình; lời nói lệch brief (vd km) → hỏi anh một câu trước khi xuất.
- Có brief đủ → không hỏi lại; chỉ hỏi thứ lời nhắc tới mà brief không có.
- Toạ độ tiện ích → điền thẳng `at` trong map.json; km anh ghi → `km`.
- Tên riêng → `realcut.py fix` ngay sau `prep`, và thêm vào `reference/sua_chinh_ta.tsv` nếu lặp lại.
