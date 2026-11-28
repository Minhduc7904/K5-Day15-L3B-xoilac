/**
 * Kịch bản tour. Chỉ khai báo, không có logic: thêm hoặc sửa bước ở đây.
 * Giọng linh vật: xưng "mình", gọi "bạn", câu ngắn, dùng "…".
 * `{name}` trong `title` được thay bằng tên người dùng (hoặc "bạn").
 */

export type TourChapterId = 'intro' | 'dashboard' | 'create' | 'result' | 'outro';

/** Tư thế linh vật khi đứng yên. `face` = tự quay mặt về phía phần tử đang chỉ. */
export type TourPose = 'welcome' | 'working' | 'studying' | 'success' | 'face';

/** `result` = trang kết quả của lượt làm mới nhất, do provider tra khi bắt đầu tour. */
export type TourPath = '/dashboard' | '/exams/new' | 'result';

export interface TourStep {
  id: string;
  chapter: TourChapterId;
  /** Trang cần đứng. Bỏ trống = giữ nguyên trang hiện tại. */
  path?: TourPath;
  /** Giá trị `data-tour` của phần tử cần khoét sáng. Bỏ trống = hộp thoại giữa màn hình. */
  target?: string;
  /** Dưới 1024px (header không có thanh điều hướng chữ) dùng target và lời khác. */
  compact?: { target?: string; body?: string };
  title: string;
  body: string;
  pose: TourPose;
}

/** Ba chặng hiển thị ở thanh tiến độ. `intro` và `outro` không tính. */
export const TOUR_CHAPTERS = [
  { id: 'dashboard', label: 'Tổng quan' },
  { id: 'create', label: 'Tạo đề' },
  { id: 'result', label: 'Kết quả' },
] as const;

export const TOUR_STEPS: readonly TourStep[] = [
  {
    id: 'welcome',
    chapter: 'intro',
    path: '/dashboard',
    title: 'Chào {name}!',
    body: 'Mình dẫn bạn đi một vòng khoảng 1 phút: xem tiến độ, nhờ mình ra đề, rồi đọc kết quả. Bạn bỏ qua lúc nào cũng được.',
    pose: 'welcome',
  },
  {
    id: 'quick-create',
    chapter: 'dashboard',
    path: '/dashboard',
    target: 'quick-create',
    title: 'Muốn ôn gì, cứ gõ vào đây',
    body: 'Ví dụ “Đề tích phân 20 phút”. Mình sẽ ghép đề từ các câu đã được duyệt trong ngân hàng câu hỏi.',
    pose: 'face',
  },
  {
    id: 'dash-chart',
    chapter: 'dashboard',
    path: '/dashboard',
    target: 'dash-chart',
    title: 'Điểm của bạn qua từng lần làm',
    body: 'Đường điểm cho thấy bạn đang tiến bộ ra sao so với mốc 8 điểm. Chạm vào một điểm để mở kết quả lần đó.',
    pose: 'studying',
  },
  {
    id: 'dash-chapters',
    chapter: 'dashboard',
    path: '/dashboard',
    target: 'dash-chapters',
    title: 'Chương nào còn yếu?',
    body: 'Chương dưới 75% câu đúng có nút ôn lại. Bấm vào là mình ra đề đúng phần đó.',
    pose: 'face',
  },
  {
    id: 'nav-create',
    chapter: 'create',
    path: '/dashboard',
    target: 'nav-create',
    compact: { target: 'nav-menu', body: 'Mở nút menu ở góc trái rồi chọn “Tạo đề với AI”. Bấm Tiếp tục, mình đi cùng bạn sang đó.' },
    title: 'Sang khu tạo đề nhé',
    body: 'Đây là nơi bạn trò chuyện với mình để dựng đề. Bấm Tiếp tục, mình đi cùng bạn sang đó.',
    pose: 'face',
  },
  {
    id: 'chat-starters',
    chapter: 'create',
    path: '/exams/new',
    target: 'chat-starters',
    title: 'Chưa biết hỏi gì? Chọn một gợi ý',
    body: 'Mỗi gợi ý là một yêu cầu hay gặp. Bạn bấm vào là mình bắt đầu ngay.',
    pose: 'working',
  },
  {
    id: 'chat-composer',
    chapter: 'create',
    path: '/exams/new',
    target: 'chat-composer',
    title: 'Nói với mình bạn cần gì',
    body: 'Mình trả lời bằng bảng cấu trúc đề. Bạn chỉnh số câu, dạng câu, độ khó rồi mới bấm dựng. Đề luôn là bản nháp cho tới khi bạn đồng ý.',
    pose: 'face',
  },
  {
    id: 'result-score',
    chapter: 'result',
    path: 'result',
    target: 'result-score',
    title: 'Nộp bài xong là thấy điểm ngay',
    body: 'Đây là trang điểm sau mỗi lần nộp bài. Điểm chỉ để bạn luyện tập, không xếp hạng ai và không so với bạn khác.',
    pose: 'success',
  },
  {
    id: 'result-review',
    chapter: 'result',
    path: 'result',
    target: 'result-review',
    title: 'Xem lại từng câu kèm lời giải',
    body: 'Lọc các câu sai, đọc lời giải và xem thời gian từng câu để biết mình chậm ở đâu.',
    pose: 'face',
  },
  {
    id: 'finish',
    chapter: 'outro',
    title: 'Xong rồi! Thử tạo đề đầu tiên nhé',
    body: 'Cần xem lại hướng dẫn thì mở menu tài khoản, chọn “Xem lại hướng dẫn”.',
    pose: 'success',
  },
];
