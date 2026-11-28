# Trang học sinh frontend

Dành cho người phát triển các trang học sinh. Hồ sơ, lịch nhắc và credit đọc từ [API hồ sơ học sinh](../api/student-profile-api.md). Dashboard, streak, đề, lượt làm và ví dụ trong tour hiện dùng dữ liệu mẫu trong trình duyệt.

## Bối cảnh và ràng buộc

Issue #9 yêu cầu bộ trang học sinh. Các ràng buộc từ [đặc tả](../../spec.md) §4 được giữ cả ở mock:

- Agent chỉ chọn câu đã duyệt trong ngân hàng. Agent không tự viết câu hỏi hay đáp án mới. Nếu ngân hàng thiếu câu, agent báo rõ số câu còn thiếu.
- Đề do AI dựng luôn là bản nháp. Học sinh xem cấu trúc và bấm "Dựng đề" thì đề mới được tạo.
- Điểm làm online là điểm luyện tập không chính thức. Không xếp hạng và không so sánh học sinh với nhau.
- Agent từ chối yêu cầu ngoài môn Toán và yêu cầu giải hộ bài thi đang diễn ra.

Câu hỏi mock do nhóm tự viết. Repo không chép câu nào từ ngân hàng thật. Ba hình minh hoạ trong `frontend/public/mock/media/` là SVG nhóm tự vẽ.

## Thành phần và trách nhiệm

| Vị trí trong `frontend/src/` | Trách nhiệm |
| --- | --- |
| `app/(student)/(app)/layout.tsx` | Bọc các trang có điều hướng bằng `AppShell` với header cố định khi cuộn và vùng nội dung toàn chiều rộng |
| `app/(student)/(app)/dashboard`, `exams`, `exams/new`, `exams/[id]`, `results/[attemptId]`, `profile` | Mỗi route chỉ render page component của feature |
| `app/(student)/(focus)/exams/[id]/take/page.tsx` | Trang làm bài toàn màn hình với thanh công cụ làm bài riêng |
| `features/study/types.ts` | Kiểu dữ liệu `Question`, `Exam`, `Attempt`, `StructureProposal` và các kiểu khác. Bám theo schema production (xem mục bên dưới) |
| `features/study/api.ts` | Điểm nối dữ liệu cho chế độ mock và API đề, lượt làm và kết quả thật |
| `features/study/mock.ts` | Kho mock trong `localStorage` key `examind:mock-study`, thống kê theo chương, chuỗi ngày học, agent giả lập `runAgent` |
| `features/study/fixtures/` | 19 câu hỏi tự viết, danh sách chương lấy từ `data/chapters.csv`, đề và lượt làm mẫu |
| `features/study/grading.ts` | Chấm và dựng kết quả cho dữ liệu mock. Kết quả thật lấy từ server |
| `features/study/use-resource.ts` | Hook tải dữ liệu, trả về `loading`, `ready` hoặc `error` cùng hàm `reload` |
| `features/study/format.ts` | Định dạng ngày, thời lượng, điểm và màu theo mức điểm |
| `features/study/components/` | `AppShell`, `StudentHeader`, `Flame`, `QuestionContent`, `PageHeader`, `EmptyState`, `ErrorState` |
| `features/onboarding/` | Tour hướng dẫn người mới: `steps.ts` (toàn bộ kịch bản và lời thoại), `tour-provider.tsx` (trạng thái, tự bật, chuyển trang), `tour-overlay.tsx` (lớp tối khoét sáng, định vị thẻ, bàn phím), `tour-mascot.tsx`, `tour-bubble.tsx`, `tour-progress.tsx`, `use-tour-target.ts`, `storage.ts`. Xem mục "Tour hướng dẫn" bên dưới |
| `features/study/dashboard/` | Lối tắt tạo đề và chuỗi học trong cùng một khối, dải số liệu, biểu đồ điểm Recharts, lịch sử đề và thống kê theo chương |
| `features/study/create/` | Trang chat với agent: cột trái quản lý đoạn chat (`sessions.ts`, lưu localStorage), bảng cấu trúc đề nổi trên khung chat (`structure-preview.tsx`), thanh kéo nhiều vạch (`segment-slider.tsx`), popup ma trận nâng cao (`matrix-dialog.tsx`), logic kế hoạch ↔ ma trận (`plan.ts`) |
| `features/study/exams/` | Danh sách đề có lọc và tìm kiếm, trang chi tiết đề (không lộ đáp án; câu hỏi chia tab theo phần, bấm ảnh để phóng to). `exam-paper.tsx` dựng bản xem đề khổ A4 (chia trang bằng cách đo chiều cao từng câu) và nút "Tải PDF" gọi `window.print()` với CSS in A4 trong `globals.css`; trang chi tiết đề và thẻ "Đề nháp đã sẵn sàng" trong chat tạo đề đều mở bản này |
| `features/study/take/` | Trang làm bài: hẹn giờ, tự lưu nháp, phím tắt, đánh dấu câu, bảng điều hướng. Đếm giây cho câu đang mở (bỏ qua lúc tab ẩn), lưu trong nháp và gửi kèm khi nộp thành `Attempt.questionSeconds` |
| `features/study/result/` | Vòng điểm, so với lượt trước, thanh kết quả theo trạng thái, nhịp độ làm bài (`pace.tsx`: biểu đồ cột thời gian từng câu tô màu theo kết quả, đường trung bình, thời gian theo phần, ba câu lâu nhất, nhận xét), phân tích theo phần và chương, xem lại từng câu kèm lời giải và thời gian. Lượt mẫu trong mock có thời gian từng câu tự sinh theo dạng câu và mức độ; lượt cũ không có `questionSeconds` thì hiện thông báo thay biểu đồ |
| `features/study/profile/` | Hồ sơ, API hồ sơ và trạng thái credit dùng chung. `/profile/setup` dùng cùng form với tab Cài đặt. `/profile#credit` và `/profile#settings` mở thẳng tab tương ứng |
| `components/math/math-content.tsx` | `MathContent`: hiển thị văn bản có công thức và hình, dùng chung cho câu hỏi, đáp án và lời giải |

## Luồng dữ liệu và tích hợp

### Dashboard học tập

Dashboard đọc `studyApi.getDashboard()`. Ô nhập và các gợi ý mở `/exams/new?q=…`. Chuỗi học dùng dấu kiểm cho ngày đã học và viền đánh dấu ngày hiện tại trong 7 ngày gần nhất. Dải tổng quan hiển thị số đề đã làm, câu đã luyện, thời gian học và điểm trung bình.

Biểu đồ dùng Recharts với thang điểm 0–10 và mốc 8 điểm. Rê chuột để xem điểm theo lượt, hoặc dùng Tab rồi Enter tại một điểm để mở kết quả. Danh sách gần đây dẫn tới cùng trang kết quả. Thống kê chương có bộ lọc lớp 10–12 và lối tắt ôn lại cho chương dưới 75% câu đúng.

Biểu đồ radar hồ sơ học tập quy đổi các chỉ số về 0–100%. Độ chính xác là tỉ lệ đúng trên các câu đã trả lời, hoàn thành bài là tỉ lệ có câu trả lời trên tổng số câu. Tốc độ lấy thời lượng đề phân bổ theo số câu đã trả lời, chia cho thời gian làm thực tế và giới hạn ở 100%. Đạt mục tiêu là tỉ lệ lượt từ 8 điểm. Bốn chỉ số này lấy tối đa 5 lượt gần nhất. Nhịp học dùng tỉ lệ ngày có học trong 7 ngày. Bảng bên cạnh biểu đồ ghi số liệu và diễn giải từng trục.

### Điều hướng và tài khoản

Từ 1024px, `StudentHeader` đặt logo bên trái, các mục học tập bằng chữ ở giữa, chuông thông báo và thẻ tài khoản bên phải. Màn hình hẹp mở các mục học tập trong sidebar trượt từ trái bằng nút menu. Cả hai dùng cùng danh sách route và đánh dấu mục hiện tại. Chiều cao header nằm ở `--student-header-height` trong `AppShell` để trang chat phân bổ phần còn lại cho nội dung và ô soạn.

Thẻ tài khoản lấy tên và email từ phiên Redux. Menu mở `/profile` và gọi `useLogout` để xóa phiên rồi chuyển tới trang đăng nhập. Tên hiển thị luôn là của người đăng nhập (`display_name`, thiếu thì dùng email). Menu có thêm mục "Xem lại hướng dẫn" để chạy lại tour. Ô credit cạnh chuông đọc cùng số dư API với tab Credit và mở `/profile#credit`. Số dư ban đầu là 500, cộng tối đa 100 mỗi ngày theo giờ Việt Nam, với trần 500. Nút chuông mở bảng thông báo với trạng thái rỗng trong lúc chờ nguồn dữ liệu.

### Định dạng nội dung câu hỏi

Nội dung câu hỏi theo đúng định dạng đang lưu ở production:

- Công thức inline viết trong `$…$`. Công thức hiển thị riêng dòng viết trong `$$…$$`.
- Hình chèn bằng `![media:ID](media:ID)`. ID trỏ tới bảng `media` (bucket và object key trong MinIO).
- Xuống dòng giữ nguyên. `**…**` là chữ đậm.

`MathContent` nhận `source` và hàm `resolveMedia(id)`. Hàm này trả `{src, alt, width, height}` hoặc `null`. Công thức được render bằng KaTeX với `throwOnError: false`, nên công thức sai cú pháp chỉ hiện chữ đỏ mà không làm hỏng trang. Hình có nút phóng to, mở trong `<dialog>`. Khi nối API thật, chỉ cần thay `resolveMedia` trong `features/study/components/question-content.tsx` để trả URL ảnh từ backend.

### Schema production (đọc ngày 2026-11-28, chỉ đọc)

| Bảng | Nội dung dùng cho frontend |
| --- | --- |
| `questions` | `content`, `type` (`SINGLE_CHOICE`, `TRUE_FALSE`, `SHORT_ANSWER`, `ESSAY`, `MULTIPLE_CHOICE`), `correct_answer`, `solution`, `difficulty` (`NB`, `TH`, `VD`, `VDC`), `grade`, `visibility` |
| `statements` | Các lựa chọn hoặc mệnh đề của câu, có `is_correct` và `order` |
| `exams`, `sections`, `questions_exams` | Đề, các phần của đề và thứ tự câu trong đề. Đề THPT có ba phần: 12 câu trắc nghiệm, 4 câu đúng sai, 6 câu trả lời ngắn |
| `media` | Ảnh gắn trong câu hỏi và lời giải |
| `chapters` | Cây chương theo lớp |

Lời giải dùng cùng định dạng với nội dung câu hỏi. Lời giải câu đúng sai có các dòng dạng `a) ĐÚNG …`.

### Chấm điểm

Đề do agent dựng có tổng tối đa 10. Backend tính điểm theo mẫu hoặc trọng số điểm theo dạng câu. Học sinh có thể chỉnh trọng số trong ma trận đề theo chương. Mỗi câu Đúng/Sai được nhân với hệ số 0%, 10%, 25%, 50% hoặc 100% theo số mệnh đề đúng. Bảng dưới mô tả cách chấm ở chế độ demo.

| Dạng câu | Điểm tối đa | Cách tính |
| --- | --- | --- |
| Trắc nghiệm một đáp án | 0,25 | Đúng được cả điểm |
| Đúng sai (4 mệnh đề) | 1 | Đúng 1, 2, 3, 4 mệnh đề được 0,1 / 0,25 / 0,5 / 1 |
| Trả lời ngắn | 0,5 | So sau khi chuẩn hoá (bỏ khoảng trắng, đổi dấu chấm thập phân thành dấu phẩy) |

Tổng điểm được quy về thang 10 theo tỉ lệ điểm đạt trên điểm tối đa của đề.

### Luồng tạo đề với agent

Với `NEXT_PUBLIC_EXAM_CHAT_LIVE=true` và mock tắt, chat, danh sách phiên, Đề của tôi và Xem đề lấy dữ liệu từ backend. Học sinh dán, tải hoặc kéo thả ảnh vào ô nhập, xem thumbnail trước khi gửi và mở lại ảnh trong lịch sử. Học sinh chỉnh ma trận tới 50 câu theo chương con và xác nhận trước khi dựng. Mỗi phiên dùng một đề nháp hiện hành. Xem [hợp đồng API](../api/user-exam-api.md#luồng-chat-thật). Nội dung phía dưới mô tả luồng demo khi tắt cờ.

1. Học sinh nhắn, có thể kèm tối đa 4 ảnh, mỗi ảnh tối đa 5 MB. Từ dashboard, lối tắt mở `/exams/new?q=…` và tin nhắn được gửi tự động.
2. `agentApi.run` trả về một async generator. Generator phát các sự kiện `text` (từng đoạn chữ), `proposal` (cấu trúc đề đề xuất) và `built` (đề đã dựng).
3. Bảng xem trước hiện cấu trúc đề. Học sinh sửa tên đề, thời gian, số câu từng phần (không vượt số câu có trong ngân hàng) và độ khó. Học sinh cũng có thể nhắn "thêm", "bớt", "khó hơn" hoặc "45 phút".
4. Khi học sinh bấm "Dựng đề" hoặc nhắn "xác nhận", agent chọn câu và trả về thẻ đề có hai nút "Làm ngay" và "Xem đề".

Trên màn hình nhỏ, bảng xem trước mở dưới dạng bottom sheet.

### Luồng làm bài

Luồng thật lưu đáp án trên server, dùng room Socket.IO theo lượt và đồng bộ lại khi mất kết nối. Nút **Làm tiếp** mở đúng lượt của tài khoản. Đồng hồ có thời lượng tiếp tục chạy khi người dùng thoát. Khi tới hạn, worker chấm và trang kết quả hiển thị thông báo hết giờ. Đề vô hạn chỉ ghi thời gian hoạt động từng câu và nộp khi học sinh chọn. Xem [API làm bài online](../api/online-exam-attempts-api.md).

Chế độ demo lưu nháp cục bộ trong `localStorage` key `examind:attempt-draft:<examId>`.

### Tour hướng dẫn

Lần đầu học sinh vào `/dashboard`, linh vật dẫn một vòng qua ba chặng: Tổng quan, Tạo đề, Kết quả (10 bước, đúng chỗ khai báo trong `features/onboarding/steps.ts`). Nền tối khoét sáng phần tử đang giới thiệu, linh vật chạy tới đó và nói. Tour tự chuyển trang `/dashboard` → `/exams/new` → `/results/<lượt mới nhất>`. Chặng Kết quả lấy lượt đầu của `studyApi.getDashboard().recent`, nên không phụ thuộc id mock; tài khoản chưa có lượt nào thì chặng này bị bỏ.

- **Điều khiển.** Mỗi bước có "Tiếp tục", "Quay lại" và "Bỏ qua hướng dẫn" (`Esc` cũng bỏ qua; `←`/`→` đi lùi/tiến). Bước chào có "Bắt đầu" và "Bỏ qua, mình tự khám phá"; bước cuối có "Tạo đề đầu tiên" và "Về Tổng quan". Trong lúc chạy, trang phía sau bị `inert` và khoá cuộn để trạng thái không lệch.
- **Tự bật.** `TourProvider` bọc `AppShell` trong `app/(student)/(app)/layout.tsx`, nên sống sót qua các lần đổi trang. Nó chỉ tự bật khi đứng ở `/dashboard`, splash đã tắt, ô tạo nhanh đã hiện và tài khoản chưa có cờ. Mở lại bằng menu tài khoản, mục "Xem lại hướng dẫn".
- **Cờ đã xem.** `localStorage` key `examind:onboarding:v1:<user_id>` với giá trị `completed` hoặc `skipped`. Đổi `VERSION` trong `storage.ts` khi nội dung tour thay đổi đủ nhiều. "Khôi phục dữ liệu mẫu" trong hồ sơ không xoá cờ này.
- **Đích của từng bước** là thuộc tính `data-tour="…"` trên phần tử có sẵn: `quick-create`, `dash-chart`, `dash-chapters`, `nav-create`, `nav-menu` (header, dưới 1024px), `chat-starters`, `chat-composer`, `result-score`, `result-review`. Đổi cấu trúc trang thì giữ các thuộc tính này; thiếu đích quá 5 giây thì bước đó tự bị bỏ qua.
- **Thêm hoặc sửa bước.** Chỉ cần sửa `steps.ts` và gắn `data-tour` vào phần tử mới. Mỗi chặng nên giữ dưới 4 bước.
- **Điện thoại.** Dưới 1024px header không có thanh điều hướng chữ nên bước "Sang khu tạo đề" trỏ vào nút menu và không mở ngăn kéo (`<dialog>` native nằm top-layer, không phủ được bằng z-index). Từ 640px trở xuống thẻ nói chiếm bề ngang, đặt ở nửa đối diện với phần tử được chỉ. Lớp tối dùng `z-[80]`: trên hộp thoại `z-50`, dưới toast `z-[90]`.
- **Giảm chuyển động.** Khi hệ điều hành bật `prefers-reduced-motion`, linh vật và khung khoét đổi chỗ ngay, không dùng dáng chạy.

### Nối API thật

Thay `studyApi` và `agentApi` trong `features/study/api.ts` bằng adapter gọi backend qua `lib/api-client.ts`, giữ nguyên chữ ký hàm. `agentApi.run` cần trả cùng loại sự kiện. Backend có thể dùng SSE, sau đó adapter đổi luồng SSE thành async generator. Lỗi "không tìm thấy" phải ném `NotFoundError` để trang hiện trạng thái phù hợp.

Các route học sinh yêu cầu đăng nhập. Với phiên thật, chốt hồ sơ chuyển học sinh thiếu hồ sơ tới `/profile/setup` trước khi render khu vực học sinh. Khi lưu thành công, vào dashboard và tour có thể bắt đầu. Chế độ auth mẫu cho phép dùng dashboard và tour để demo.

## Quyết định và cách kiểm chứng

- **Không xếp hạng.** Dashboard chỉ so học sinh với chính mình: điểm qua các lượt, lượt trước và mục tiêu 8 điểm.
- **Màu chuỗi học** dùng `flame-subtle` cho nền và `flame-strong` cho các điểm nhấn trong dashboard.
- **Tràn ngang trên điện thoại.** Phần tử con của grid mặc định có `min-width: auto` nên bị tràn. `globals.css` đặt `:where(.grid) > * { min-width: 0 }` để tránh lỗi này.
- **KaTeX** được ghim phiên bản `0.19.1`. CSS của KaTeX nằm trong `math-content.tsx`.

Cách kiểm chứng:

```powershell
cd frontend; npm run typecheck; npm run build
```

Chạy `npm run dev`, đăng nhập rồi mở `http://localhost:3000/dashboard`. Kiểm tra ở bề rộng 375px và 1280px:

- Các trang không có thanh cuộn ngang.
- Trong dashboard, kiểm tra ô tạo đề mở chat với đúng nội dung, chuỗi học đánh dấu hôm nay, điểm trên biểu đồ mở kết quả bằng phím Enter và bộ lọc chương giới hạn đúng lớp.
- Kiểm tra mục đang chọn ở `/exams/new` và `/exams`, sidebar mobile mở và đóng bằng phím Escape, chuông mở bảng thông báo, và menu tài khoản có thể vào hồ sơ rồi đăng xuất.
- Công thức không có phần tử `.katex-error`.
- Có thể làm bài, tải lại trang rồi làm tiếp, sau đó nộp bài và xem kết quả.
- Trong `/exams/new`, gửi "Ôn chương mình hay sai, đề 30 phút", bấm "Dựng đề", rồi mở đề vừa tạo.
- Trong bảng cấu trúc đề: chọn thời gian ∞ (không giới hạn), kéo vạch cuối của "Dạng câu" để đổi tổng (tối đa 50), thấy nút đổi thành "Để agent phân bổ lại"; bấm nút đó, rồi mở "Nâng cao" để sửa từng ô ma trận chương con × dạng × mức độ và "Áp dụng ma trận". Tải lại trang, đoạn chat vẫn còn ở cột trái.

Nút "Khôi phục dữ liệu mẫu" trong trang hồ sơ đưa kho mock về dữ liệu ban đầu.

## Tài liệu liên quan

- [Đặc tả](../../spec.md) §4 và §7
- [Kiến trúc frontend](frontend-base.md)
- [Design system frontend](frontend-design-system.md)
- [Trang xác thực frontend](frontend-auth.md)
