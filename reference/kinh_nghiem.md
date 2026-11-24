# Kinh nghiệm dựng realcut (gợi ý — dùng khi hợp với kịch bản của anh Vũ)
Câu hỏi chung: **người xem đang lướt — vì sao họ dừng lại ở giây này?**

## Minh hoạ theo lời
Anh nói tới đâu, hình tới đó (sớm 2–4 khung).
- Dự án: nói tên → phối cảnh/flycam dự án; nói vị trí → flycam + nhãn đường; nói ưu đãi/thanh toán → số % / thẻ từng phương án.
- Đất nền: nói vị trí → flycam từ điểm mốc dễ nhận về lô; nói thông số → thẻ ngang × dài, thổ cư, hướng, lộ giới.
- Nhà phố: nói tới phòng nào → cảnh phòng đó; cảnh trong nhà nối cùng hướng đi như khách đang đi xem.

- Nói khoảng cách tới tiện ích ("cách chợ 2 km, bệnh viện 5 phút") → bản đồ khoảng cách (`map`), mỗi tiện ích hiện đúng lúc được nhắc; flycam thật vẫn hơn bản đồ khi chỉ nói chung chung "vị trí đẹp".

## Người xem Reels
- Nhiều người xem tắt tiếng: ý quan trọng chỉ nằm trong lời → nên có chữ.
- 3 s đầu quyết định xem tiếp: khung đầu có hình mạnh + chữ cho câu mở đầu, chuyển động sớm, tránh mở từ màn đen/logo. Khung đầu = ảnh bìa. Chạy ads → có thể đề xuất 2–3 biến thể mở đầu để A/B (anh quyết).
- Một màn hình một ý; chữ đặt vào vùng trống của hình.
- Thời gian đọc tham khảo: ≥ 0.3 s + 0.2 s/từ (tối thiểu 0.8 s); giá, %, hotline ≥ 1.5–2 s.

## Nhịp
Thường có thông tin mới mỗi 2–3 s; mặt người nói lâu không có ý mới → cân nhắc B-roll/zoom. Trước chỗ anh nhấn mạnh nhất có thể chậm một nhịp rồi bung. Dành cảnh đẹp nhất cho mở đầu và chỗ nhấn đó.

## Cú cắt
Cắt theo lời (cuối từ khoá / đầu câu) hoặc phách nhạc, không cắt giữa từ · hai cảnh liền nhau cùng hướng chuyển động máy, cắt khi máy đang chuyển động · mở đoạn mới bằng cảnh toàn rồi vào gần; tránh nối hai cảnh cùng cỡ cùng góc · chỗ này cần TIN (mặt anh), THẤY (B-roll) hay NHỚ (chữ vàng nhũ)?

## Chữ
Hiện khi cảnh khớp chữ (vd "SIÊU TRUNG TÂM" khi đã vào cảnh TTTM), giữ đến khi chuyển cảnh · thẻ số liệu không chồng chữ lớn · hai ý ngang nhau → `layout: stack3` · thẻ liệt kê dồn xuống đáy vùng an toàn.

## Âm thanh
SFX trước hình 1–2 khung, thưa (nhiều SFX nghe rẻ) · nhạc dưới giọng, lên khi không có lời · drop ở chỗ anh nhấn mạnh nhất (thường câu giá) · có thể lặng ngắn trước chỗ đó.

## Kết
Theo câu kết trong kịch bản; hotline ~2 s để kịp chụp màn hình; khung cuối nối được về khung đầu để video lặp mượt.

## Soát bằng mắt (`fx --sheet 0.5`)
(1) chỉ hình + chữ có kể đúng câu chuyện anh nói? (2) âm thanh final: từ bị cắt, nhạc đè giọng? (3) nhịp: chuyển động ngược chiều, hai cảnh cùng cỡ nối nhau, chữ chồng chữ? (4) khung đầu và 3 s đầu.

## Bài học từ video đất nền đã duyệt (Tránh Đông 10×15, 11/2026)
- Chữ không bao giờ che người; các khối (giá, đồ hoạ, từ khoá) nối tiếp, chừa ~0.3 s, không chồng.
- Nhạc là nền nhưng phải nghe thấy: có lời thì nhạc thấp hơn giọng ~15 dB (anh Vũ chốt 22/11), lúc ngừng/chuyển cảnh nhạc tự dâng (duck). SFX nhẹ, luôn dưới giọng. Đổi nhạc: chọn Mixkit theo mood, tải https://assets.mixkit.co/music/<id>/<id>.mp3 (đã duyệt: 837 Life is a Dream).
- Mức âm mặc định (anh Vũ chốt 22/11, ERA City 7,5 tỷ v2, đo stem demucs + ebur128): giọng ≈ −14.3 LUFS, nhạc+SFX ≈ −25.5 LUFS, tổng −14 LUFS · có lời: nhạc ~15 dB dưới giọng · chuyển cảnh: nhạc + whoosh 2–7 dB dưới giọng. mix.py: `MUSIC_GAIN 1.1`, `SFX_GAIN_DB +11`, `VOICE_RATIO 2.5`, `VOICE_CLARITY 1` (cắt <100 Hz, −2.5 dB 250 Hz, +3 dB 3.2 kHz, +2.5 dB 5 kHz, +3 dB shelf 8 kHz, de-esser), duck ratio 4 / threshold 0.03, `LUFS −14`. Đổi mức thì đo lại: `demucs --two-stems=vocals` rồi ebur128 từng stem.
- Kiểm tra mức nhạc/giọng bằng số đo, không đoán: tách stem (demucs --two-stems=vocals) rồi đo LUFS từng stem.
- Đồ hoạ phối cảnh không được làm sai tỉ lệ (dài 15 phải trông dài hơn ngang 10).

## Mức âm (anh Vũ chốt 22/11/2026)

## Bài học từ video đất nền đã duyệt (15 lô Ea Ning 450 tr, final v5, 24/11/2026)
- Storyboard trước, dựng sau: anh sửa bảng phân cảnh (xlsx) rồi mới chạy base/fx — tiết kiệm nhiều vòng nháp.
- Bản đồ là xương sống phần vị trí: ranh xã → zoom liền mạch vào lô → đường đi tới từng tiện ích (thẻ ảnh/video bật ra khi đường tới nơi) → toàn cảnh có bán kính. Không cắt cứng giữa các bản đồ cùng khu vực.
- Hình minh hoạ của chính lô (sơ đồ phân lô) phải gắn với ghim: bung ra từ ghim đúng câu nói về lô, rồi thu về — không để thẻ đứng suốt che đường.
- Quy hoạch lân cận: vẽ ranh trên vệ tinh khớp đường thật + quét lộ phối cảnh; ghi rõ "minh hoạ"; số liệu (66,8 ha) lấy theo bản vẽ, hỏi anh khi lời nói làm tròn.
- Khoảng cách anh nói lệch số đo (vd thác 700 m vs 1,3 km đường bộ) → hiện số anh nói nhưng báo anh trong báo cáo, caption không ghi số đó.
- Nhạc: một bài chạy liền từ đầu (dời đoạn hay nhất của bài lên đầu) hay hơn ghép bài mở đầu khác. Tiếng hiệu ứng có nghĩa: giá = tính tiền, tăng giá = apple pay, thông số = pop, ý chốt = boom, chuyển cảnh = whoosh, bản đồ = tiếng chạy ranh.
- Nháp 540p 15 khung/s nhìn giựt — khi anh chê "giựt" trước hết xuất 1080p 30 khung/s cho anh xem độ mượt thật.
