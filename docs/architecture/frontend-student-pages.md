# Trang học sinh frontend

Dành cho người phát triển các trang học sinh. Hồ sơ, lịch nhắc và credit đọc từ [API hồ sơ học sinh](../api/student-profile-api.md). Dashboard, streak, đề, lượt làm, kết quả và thông báo đọc từ API thật của backend. Chỉ có một bộ kết quả minh hoạ tĩnh cho tour hướng dẫn (xem mục "Tour hướng dẫn").

## Bối cảnh và ràng buộc

Issue #9 yêu cầu bộ trang học sinh. Các ràng buộc từ [đặc tả](../../spec.md) §4 được giữ ở bản chạy:

- Agent chỉ chọn câu đã duyệt trong ngân hàng. Agent không tự viết câu hỏi hay đáp án mới. Nếu ngân hàng thiếu câu, agent báo rõ số câu còn thiếu.
- Đề do AI dựng luôn là bản nháp. Học sinh xem cấu trúc và bấm "Dựng đề" thì đề mới được tạo.
- Điểm làm online là điểm luyện tập không chính thức. Không xếp hạng và không so sánh học sinh với nhau.
- Agent từ chối yêu cầu ngoài môn Toán và yêu cầu giải hộ bài thi đang diễn ra.

Frontend không chứa câu hỏi hay đáp án nào: đề, câu hỏi, ảnh và lời giải đều do backend trả. Bộ minh hoạ của tour (`features/onboarding/demo-result.ts`) là 6 câu nhóm tự viết, chỉ gồm chữ và công thức.

## Thành phần và trách nhiệm

| Vị trí trong `frontend/src/` | Trách nhiệm |
| --- | --- |
| `app/(student)/(app)/layout.tsx` | Bọc các trang có điều hướng bằng `AppShell` với header cố định khi cuộn và vùng nội dung toàn chiều rộng |
| `app/(student)/(app)/dashboard`, `exams`, `exams/new`, `exams/[id]`, `results/[attemptId]`, `profile` | Mỗi route chỉ render page component của feature |
| `app/(student)/(focus)/exams/[id]/take/page.tsx` | Trang làm bài toàn màn hình với thanh công cụ làm bài riêng |
| `features/study/types.ts` | Kiểu dữ liệu `Question`, `Exam`, `Attempt`, `StructureProposal` và các kiểu khác. Bám theo schema production (xem mục bên dưới) |
| `features/study/api.ts` | `studyApi`: điểm nối dữ liệu duy nhất của trang học sinh (dashboard, danh sách đề, đề, kết quả). Ghép `dashboard-api.ts`, `attempt-api.ts`, `exam-chat-api.ts` và danh mục chương |
| `features/study/dashboard-api.ts` | `GET /study/dashboard` và adapter sang `DashboardData` (id `online-N`, `draft-N`) |
| `features/study/chapters.ts` | Danh mục chương nạp một lần từ `GET /exam-chat/chapters`; `chapterOf(code)` trả tên chương, thiếu thì hiện mã |
| `features/study/labels.ts` | Nhãn tiếng Việt và màu của dạng câu, mức độ |
| `features/study/errors.ts` | `NotFoundError` để trang hiện trạng thái "không tìm thấy" thay vì lỗi chung |
| `features/study/grading.ts` | Kiểu `QuestionResult` và hàm hiển thị điểm. Việc chấm do backend làm |
| `features/study/use-resource.ts` | Hook tải dữ liệu, trả về `loading`, `ready` hoặc `error` cùng hàm `reload` |
| `features/study/format.ts` | Định dạng ngày, thời lượng, điểm và màu theo mức điểm |
| `features/study/components/` | `AppShell`, `StudentHeader`, `Flame`, `QuestionContent`, `PageHeader`, `EmptyState`, `ErrorState` |
| `features/onboarding/` | Tour hướng dẫn người mới: `steps.ts` (toàn bộ kịch bản và lời thoại), `tour-provider.tsx` (trạng thái, tự bật, chuyển trang), `tour-overlay.tsx` (lớp tối khoét sáng, định vị thẻ, bàn phím), `tour-mascot.tsx`, `tour-bubble.tsx`, `tour-progress.tsx`, `use-tour-target.ts`, `storage.ts`. Xem mục "Tour hướng dẫn" bên dưới |
| `features/notifications/` | Chuông thông báo: `api.ts`, hook `use-notifications.ts` (tải, đánh dấu đã đọc, nhận `notification:new`, tải lại khi kết nối lại), `notification-panel.tsx`. Xem [API thông báo](../api/notifications-api.md) |
| `features/study/dashboard/` | Lối tắt tạo đề và chuỗi học trong cùng một khối, dải số liệu, biểu đồ điểm Recharts, lịch sử đề và thống kê theo chương |
| `features/study/create/` | Trang chat tạo đề với agent (`live-create-exam-page.tsx`, ô soạn, thẻ đề nháp). Phiên chat và ma trận đề lưu ở backend |
| `features/study/exams/` | Danh sách đề có lọc và tìm kiếm, trang chi tiết đề (không lộ đáp án; câu hỏi chia tab theo phần, bấm ảnh để phóng to). `exam-paper.tsx` dựng bản xem đề khổ A4 (chia trang bằng cách đo chiều cao từng câu) và nút "Tải PDF" gọi `window.print()` với CSS in A4 trong `globals.css`; trang chi tiết đề và thẻ "Đề nháp đã sẵn sàng" trong chat tạo đề đều mở bản này |
| `features/study/take/` | Trang làm bài: hẹn giờ theo giờ server, tự lưu đáp án lên server, phím tắt, đánh dấu câu, bảng điều hướng. Thời gian mở từng câu gửi kèm khi lưu và trở thành `Attempt.questionSeconds` |
| `features/study/result/` | Vòng điểm, so với lượt trước, thanh kết quả theo trạng thái, nhịp độ làm bài (`pace.tsx`: biểu đồ cột thời gian từng câu tô màu theo kết quả, đường trung bình, thời gian theo phần, ba câu lâu nhất, nhận xét), phân tích theo phần và chương, xem lại từng câu kèm lời giải và thời gian. Lượt cũ không có `questionSeconds` thì hiện thông báo thay biểu đồ |
| `features/study/profile/` | Hồ sơ, API hồ sơ và trạng thái credit dùng chung. `/profile/setup` dùng cùng form với tab Cài đặt. `/profile#credit` và `/profile#settings` mở thẳng tab tương ứng |
| `components/math/math-content.tsx` | `MathContent`: hiển thị văn bản có công thức và hình, dùng chung cho câu hỏi, đáp án và lời giải |

## Luồng dữ liệu và tích hợp

### Dashboard học tập

Dashboard đọc `studyApi.getDashboard()` (`GET /study/dashboard`, xem [API dashboard](../api/study-dashboard-api.md)). Số liệu tính từ các lượt đã chấm: chuỗi học là số ngày liên tiếp (giờ Việt Nam) có ít nhất một lượt được chấm, thống kê chương gộp theo chương cha và chỉ tính câu đúng hoàn toàn. Tài khoản chưa có lượt nào thấy trạng thái rỗng. Ô nhập và các gợi ý mở `/exams/new?q=…`. Chuỗi học dùng dấu kiểm cho ngày đã học và viền đánh dấu ngày hiện tại trong 7 ngày gần nhất. Dải tổng quan hiển thị số đề đã làm, câu đã luyện, thời gian học và điểm trung bình.

Biểu đồ dùng Recharts với thang điểm 0–10 và mốc 8 điểm. Rê chuột để xem điểm theo lượt, hoặc dùng Tab rồi Enter tại một điểm để mở kết quả. Danh sách gần đây dẫn tới cùng trang kết quả. Thống kê chương có bộ lọc lớp 10–12 và lối tắt ôn lại cho chương dưới 75% câu đúng.

Biểu đồ radar hồ sơ học tập quy đổi các chỉ số về 0–100%. Độ chính xác là tỉ lệ đúng trên các câu đã trả lời, hoàn thành bài là tỉ lệ có câu trả lời trên tổng số câu. Tốc độ lấy thời lượng đề phân bổ theo số câu đã trả lời, chia cho thời gian làm thực tế và giới hạn ở 100%. Đạt mục tiêu là tỉ lệ lượt từ 8 điểm. Bốn chỉ số này lấy tối đa 5 lượt gần nhất. Nhịp học dùng tỉ lệ ngày có học trong 7 ngày. Bảng bên cạnh biểu đồ ghi số liệu và diễn giải từng trục.

### Điều hướng và tài khoản

Từ 1024px, `StudentHeader` đặt logo bên trái, các mục học tập bằng chữ ở giữa, chuông thông báo và thẻ tài khoản bên phải. Màn hình hẹp mở các mục học tập trong sidebar trượt từ trái bằng nút menu. Cả hai dùng cùng danh sách route và đánh dấu mục hiện tại. Chiều cao header nằm ở `--student-header-height` trong `AppShell` để trang chat phân bổ phần còn lại cho nội dung và ô soạn.

Thẻ tài khoản lấy tên và email từ phiên Redux. Menu mở `/profile` và gọi `useLogout` để xóa phiên rồi chuyển tới trang đăng nhập. Tên hiển thị luôn là của người đăng nhập (`display_name`, thiếu thì dùng email). Menu có thêm mục "Xem lại hướng dẫn" để chạy lại tour. Ô credit cạnh chuông đọc cùng số dư API với tab Credit và mở `/profile#credit`. Số dư ban đầu là 500, cộng tối đa 100 mỗi ngày theo giờ Việt Nam, với trần 500. Nút chuông hiện số thông báo chưa đọc và mở danh sách thông báo thật: bài hết giờ đã tự chấm, đề nháp dựng xong, cộng credit hằng ngày và nhắc lịch học. Thông báo mới tới qua Socket.IO, danh sách tải lại khi kết nối lại hoặc khi tab hiện lại.

### Định dạng nội dung câu hỏi

Nội dung câu hỏi theo đúng định dạng đang lưu ở production:

- Công thức inline viết trong `$…$`. Công thức hiển thị riêng dòng viết trong `$$…$$`.
- Hình chèn bằng `![media:ID](media:ID)`. ID trỏ tới bảng `media` (bucket và object key trong MinIO).
- Xuống dòng giữ nguyên. `**…**` là chữ đậm.

`MathContent` nhận `source` và hàm `resolveMedia(id)`. Hàm này trả `{src, alt, width, height}` hoặc `undefined`. Công thức được render bằng KaTeX với `throwOnError: false`, nên công thức sai cú pháp chỉ hiện chữ đỏ mà không làm hỏng trang. Hình có nút phóng to, mở trong `<dialog>`. `QuestionContent` (`features/study/components/question-content.tsx`) trả URL ảnh của backend theo đề nháp (`draftId`) hoặc theo lượt làm (`attemptId`); không truyền cả hai thì nội dung không có ảnh.

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

Đề do agent dựng có tổng tối đa 10. Backend tính điểm theo mẫu hoặc trọng số điểm theo dạng câu. Học sinh có thể chỉnh trọng số trong ma trận đề theo chương. Mỗi câu Đúng/Sai được nhân với hệ số 0%, 10%, 25%, 50% hoặc 100% theo số mệnh đề đúng. Bảng dưới là cách backend chấm; frontend chỉ hiển thị.

| Dạng câu | Điểm tối đa | Cách tính |
| --- | --- | --- |
| Trắc nghiệm một đáp án | 0,25 | Đúng được cả điểm |
| Đúng sai (4 mệnh đề) | 1 | Đúng 1, 2, 3, 4 mệnh đề được 0,1 / 0,25 / 0,5 / 1 |
| Trả lời ngắn | 0,5 | So sau khi chuẩn hoá (bỏ khoảng trắng, đổi dấu chấm thập phân thành dấu phẩy) |

Tổng điểm được quy về thang 10 theo tỉ lệ điểm đạt trên điểm tối đa của đề.

### Luồng tạo đề với agent

Chat, danh sách phiên, Đề của tôi và Xem đề lấy dữ liệu từ backend. Học sinh dán, tải hoặc kéo thả ảnh vào ô nhập, xem thumbnail trước khi gửi và mở lại ảnh trong lịch sử. Học sinh chỉnh ma trận tới 50 câu theo chương con và xác nhận trước khi dựng. Mỗi phiên dùng một đề nháp hiện hành. Xem [hợp đồng API](../api/user-exam-api.md#luồng-chat-thật).

1. Học sinh nhắn, có thể kèm tối đa 4 ảnh, mỗi ảnh tối đa 5 MB. Từ dashboard, lối tắt mở `/exams/new?q=…` và tin nhắn được gửi tự động.
2. Agent đề xuất cấu trúc đề. Học sinh sửa tên đề, thời gian, số câu từng phần (không vượt số câu có trong ngân hàng) và độ khó, hoặc nhắn "thêm", "bớt", "khó hơn", "45 phút".
3. Khi học sinh bấm "Dựng đề" hoặc nhắn "xác nhận", agent chọn câu từ ngân hàng và trả về thẻ đề có hai nút "Làm ngay" và "Xem đề". Dựng xong thì chuông có thêm một thông báo.

Trên màn hình nhỏ, bảng xem trước mở dưới dạng bottom sheet. Backend dùng mô hình khi cấu hình đủ và rơi về bộ quy tắc khi thiếu cấu hình, frontend không cần biết.

### Luồng làm bài

Luồng thật lưu đáp án trên server, dùng room Socket.IO theo lượt và đồng bộ lại khi mất kết nối. Nút **Làm tiếp** mở đúng lượt của tài khoản. Đồng hồ có thời lượng tiếp tục chạy khi người dùng thoát. Khi tới hạn, worker chấm và trang kết quả hiển thị thông báo hết giờ. Đề vô hạn chỉ ghi thời gian hoạt động từng câu và nộp khi học sinh chọn. Xem [API làm bài online](../api/online-exam-attempts-api.md).

### Tour hướng dẫn

Lần đầu học sinh vào `/dashboard`, linh vật dẫn một vòng qua ba chặng: Tổng quan, Tạo đề, Kết quả (10 bước, đúng chỗ khai báo trong `features/onboarding/steps.ts`). Nền tối khoét sáng phần tử đang giới thiệu, linh vật chạy tới đó và nói. Tour tự chuyển trang `/dashboard` → `/exams/new` → `/results/<id>`. Chặng Kết quả lấy lượt đầu của `studyApi.getDashboard().recent`. Tài khoản chưa có lượt nào thì chặng này mở `/results/demo`, một kết quả minh hoạ tĩnh (`features/onboarding/demo-result.ts`) có biểu ngữ "Kết quả minh hoạ, không phải bài của bạn"; nó không ghi vào cơ sở dữ liệu và không tính vào dashboard hay chuỗi học. Nếu không gọi được dashboard thì chặng Kết quả bị bỏ.

- **Điều khiển.** Mỗi bước có "Tiếp tục", "Quay lại" và "Bỏ qua hướng dẫn" (`Esc` cũng bỏ qua; `←`/`→` đi lùi/tiến). Bước chào có "Bắt đầu" và "Bỏ qua, mình tự khám phá"; bước cuối có "Tạo đề đầu tiên" và "Về Tổng quan". Trong lúc chạy, trang phía sau bị `inert` và khoá cuộn để trạng thái không lệch.
- **Tự bật.** `TourProvider` bọc `AppShell` trong `app/(student)/(app)/layout.tsx`, nên sống sót qua các lần đổi trang. Nó chỉ tự bật khi đứng ở `/dashboard`, splash đã tắt, ô tạo nhanh đã hiện và tài khoản chưa có cờ. Mở lại bằng menu tài khoản, mục "Xem lại hướng dẫn".
- **Cờ đã xem.** `localStorage` key `examind:onboarding:v1:<user_id>` với giá trị `completed` hoặc `skipped`. Đổi `VERSION` trong `storage.ts` khi nội dung tour thay đổi đủ nhiều. Bootstrap chỉ dọn các khoá dữ liệu mẫu cũ (`examind:mock-study`, `examind:attempt-draft:*`, `examind:chat-sessions:v1`, `examind:mock-auth`), không đụng khoá này.
- **Đích của từng bước** là thuộc tính `data-tour="…"` trên phần tử có sẵn: `quick-create`, `dash-chart`, `dash-chapters`, `nav-create`, `nav-menu` (header, dưới 1024px), `chat-starters`, `chat-composer`, `result-score`, `result-review`. Đổi cấu trúc trang thì giữ các thuộc tính này; thiếu đích quá 5 giây thì bước đó tự bị bỏ qua.
- **Thêm hoặc sửa bước.** Chỉ cần sửa `steps.ts` và gắn `data-tour` vào phần tử mới. Mỗi chặng nên giữ dưới 4 bước.
- **Điện thoại.** Dưới 1024px header không có thanh điều hướng chữ nên bước "Sang khu tạo đề" trỏ vào nút menu và không mở ngăn kéo (`<dialog>` native nằm top-layer, không phủ được bằng z-index). Từ 640px trở xuống thẻ nói chiếm bề ngang, đặt ở nửa đối diện với phần tử được chỉ. Lớp tối dùng `z-[80]`: trên hộp thoại `z-50`, dưới toast `z-[90]`.
- **Giảm chuyển động.** Khi hệ điều hành bật `prefers-reduced-motion`, linh vật và khung khoét đổi chỗ ngay, không dùng dáng chạy.

### Nguồn dữ liệu và lỗi

Component chỉ gọi `studyApi` (và `examChatApi`, `attemptApi` ở trang chat, làm bài), không gọi Axios trực tiếp. Lỗi "không tìm thấy" ném `NotFoundError` để trang hiện trạng thái phù hợp. Id đề có dạng `draft-N`, id kết quả có dạng `online-N`; id khác (trừ `demo`) là không tìm thấy.

Các route học sinh yêu cầu đăng nhập. Với phiên thật, chốt hồ sơ chuyển học sinh thiếu hồ sơ tới `/profile/setup` trước khi render khu vực học sinh. Khi lưu thành công, vào dashboard và tour có thể bắt đầu.

## Quyết định và cách kiểm chứng

- **Không xếp hạng.** Dashboard chỉ so học sinh với chính mình: điểm qua các lượt, lượt trước và mục tiêu 8 điểm.
- **Màu chuỗi học** dùng `flame-subtle` cho nền và `flame-strong` cho các điểm nhấn trong dashboard.
- **Tràn ngang trên điện thoại.** Phần tử con của grid mặc định có `min-width: auto` nên bị tràn. `globals.css` đặt `:where(.grid) > * { min-width: 0 }` để tránh lỗi này.
- **KaTeX** được ghim phiên bản `0.19.1`. CSS của KaTeX nằm trong `math-content.tsx`.

Cách kiểm chứng:

```powershell
cd frontend; npm run typecheck; npm run build
```

Chạy backend ([run-local-stack.md](../operations/run-local-stack.md)) và `npm run dev`, đăng nhập rồi mở `http://localhost:3000/dashboard`. Kiểm tra ở bề rộng 375px và 1280px:

- Các trang không có thanh cuộn ngang.
- Trong dashboard, kiểm tra ô tạo đề mở chat với đúng nội dung, chuỗi học đánh dấu hôm nay, điểm trên biểu đồ mở kết quả bằng phím Enter và bộ lọc chương giới hạn đúng lớp.
- Kiểm tra mục đang chọn ở `/exams/new` và `/exams`, sidebar mobile mở và đóng bằng phím Escape, chuông mở bảng thông báo, và menu tài khoản có thể vào hồ sơ rồi đăng xuất.
- Công thức không có phần tử `.katex-error`.
- Có thể làm bài, tải lại trang rồi làm tiếp, sau đó nộp bài và xem kết quả.
- Trong `/exams/new`, gửi "Ôn chương mình hay sai, đề 30 phút", bấm "Dựng đề", rồi mở đề vừa tạo.
- Trong bảng cấu trúc đề: chọn thời gian ∞ (không giới hạn), kéo vạch cuối của "Dạng câu" để đổi tổng (tối đa 50), thấy nút đổi thành "Để agent phân bổ lại"; bấm nút đó, rồi mở "Nâng cao" để sửa từng ô ma trận chương con × dạng × mức độ và "Áp dụng ma trận". Tải lại trang, đoạn chat vẫn còn ở cột trái.

## Tài liệu liên quan

- [Đặc tả](../../spec.md) §4 và §7
- [Kiến trúc frontend](frontend-base.md)
- [Design system frontend](frontend-design-system.md)
- [Trang xác thực frontend](frontend-auth.md)
- [API dashboard học tập](../api/study-dashboard-api.md)
- [API thông báo](../api/notifications-api.md)
