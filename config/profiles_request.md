Media của tôi là dùng chủ yếu cho tính năgg cung cấp template mẫu cho user có thể dùng nó để chạy task AI cho tính năng đổi mặt mình vào mặt nhân vật trong video
Đầu vào là video/image do admin upload lên hệ thống.
Media có kích thuơcs khổ dọc 3*4 hoặc khác một xíu.
Cần transcode 1 media đầu vào thành các profiles đầu ra theo yêu cầu và mục đích như sau:
- Đối với một media chúng tôi có 3 nhu cầu sau:
  + hiển thị bản xem trước (đối với video), bản xem trước k cần âm thanh, và được cắt ngắn hơn fps nhỏ, và tốc độ phát nhanh, lặp vô hạn. Và dạng thumb đối với image. trên một màn hình mobile ngang chúng tôi thường hiển thị 2 media 3*4 là vừa khớp.
  + Hiện thị dạng chi tiết detail (video lớn hơn, có âm thanh, image lớn) ở màn hình detail từng template khi user chọn
  + 1 profile cho việc AI xử lý: Video có âm thanh (mp4), image lớn (tuy nhiên cả video và image này cần transscode về 1 chuẩn cụ thể, k vượt quá maxwidhr và max height đã config)

TUy nhiên hệ thống chúng tôi đang phục vụ cho nhiều phân khúc nhiều loại thiết bị mobile mạnh yếu khác nhau.
ĐỐi với các thiết bị mạnh độ phân giải cao thì cần profile cao hơn 1 xíu (cho cả 3 nhu cầu thumb/preview và detail, và cả media ai process)
Đối với các thiết bị thấp thì cần giảm chất lượng xuống so với tier cao để đảm bảo việc hiển thị.

Về yêu cầu format chúng tôi muốn bản preview video cần có 2 profile: webp và cả mp4 (cho trường hợp các device không load được ảnh webp)
về hình ảnh cũng vậy ở dạng thumb va dạng detail thì cần cả webp và jpg
Về hình ảnh cho ai xử lý thì video thì buộc là mp4 có âm thanh, hình ảnh là jpg/png tuỳ vào input user.


các profile cần define sẵn maxwidht và max hieht, k lệ thuộc vào inout từ phía amdin upload lên.



Tôi cần tạo 1 file đáp ứng đầy đủ các profile cho yêu cầu của tôi ở trên.

tạo file json cho tôi