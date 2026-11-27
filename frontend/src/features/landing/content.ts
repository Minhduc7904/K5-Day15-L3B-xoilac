import type { NavLink } from '@/components/layout/navbar';

export const landingLinks: NavLink[] = [
  { href: '#van-de', label: 'Vấn đề' },
  { href: '#cach-hoat-dong', label: 'Cách hoạt động' },
  { href: '#diem-noi-bat', label: 'Điểm nổi bật' },
  { href: '#hoi-dap', label: 'Hỏi đáp' },
];

/** Tên chương lấy từ data/chapters.csv (các chương cấp 0 có câu trong ngân hàng mẫu). */
export const chapters: Array<{ grade: 10 | 11 | 12; name: string }> = [
  { grade: 10, name: 'Mệnh đề và tập hợp' },
  { grade: 10, name: 'Bất phương trình bậc nhất hai ẩn' },
  { grade: 10, name: 'Hệ thức lượng trong tam giác' },
  { grade: 10, name: 'Vectơ' },
  { grade: 10, name: 'Hàm số, đồ thị và ứng dụng' },
  { grade: 10, name: 'Toạ độ trong mặt phẳng' },
  { grade: 10, name: 'Đại số tổ hợp' },
  { grade: 10, name: 'Xác suất cổ điển' },
  { grade: 11, name: 'Lượng giác' },
  { grade: 11, name: 'Dãy số, cấp số cộng, cấp số nhân' },
  { grade: 11, name: 'Quan hệ song song trong không gian' },
  { grade: 11, name: 'Giới hạn, hàm số liên tục' },
  { grade: 11, name: 'Hàm số mũ và lôgarit' },
  { grade: 11, name: 'Quan hệ vuông góc trong không gian' },
  { grade: 11, name: 'Quy tắc tính xác suất' },
  { grade: 11, name: 'Đạo hàm' },
  { grade: 12, name: 'Ứng dụng đạo hàm' },
  { grade: 12, name: 'Vectơ trong không gian' },
  { grade: 12, name: 'Nguyên hàm và tích phân' },
  { grade: 12, name: 'Toạ độ trong không gian' },
  { grade: 12, name: 'Xác suất có điều kiện' },
  { grade: 12, name: 'Mẫu số liệu ghép nhóm' },
];

export const difficulties = [
  { code: 'NB', name: 'Nhận biết', hint: 'Nhớ đúng công thức, định nghĩa' },
  { code: 'TH', name: 'Thông hiểu', hint: 'Áp dụng trực tiếp một bước' },
  { code: 'VD', name: 'Vận dụng', hint: 'Phối hợp nhiều bước giải' },
  { code: 'VDC', name: 'Vận dụng cao', hint: 'Bài khó, cần biến đổi sâu' },
] as const;

export const faqs = [
  {
    id: 'tu-viet',
    title: 'Examind có tự viết câu hỏi không?',
    content:
      'Không. Examind chỉ chọn và ghép các câu đã được duyệt có sẵn trong ngân hàng câu hỏi. Examind không tự viết câu hỏi hay đáp án mới.',
  },
  {
    id: 'can-cu',
    title: 'Examind dựa vào đâu để biết mình yếu chương nào?',
    content:
      'Dựa trên lịch sử làm bài của bạn: số câu đúng và sai theo từng chương. Khi đề xuất, Examind luôn nêu số liệu làm căn cứ để bạn tự kiểm tra lại.',
  },
  {
    id: 'chua-co-du-lieu',
    title: 'Nếu mình chưa làm đề nào thì sao?',
    content:
      'Examind sẽ nói rõ là chưa có dữ liệu và hỏi bạn muốn ôn chương nào, thay vì đoán chương yếu cho bạn.',
  },
  {
    id: 'chinh-de',
    title: 'Mình có chỉnh được đề trước khi tạo không?',
    content:
      'Có. Bạn xem trước cấu trúc đề gồm chương, số câu và độ khó, rồi chỉnh bằng lời, ví dụ "bớt câu vận dụng cao". Chỉ khi bạn xác nhận, Examind mới ghép đề nháp.',
  },
  {
    id: 'cham-diem',
    title: 'Examind có chấm điểm hay cho đáp án đề kiểm tra trên lớp không?',
    content:
      'Không. Examind không ghi điểm chính thức, không xếp hạng học sinh và không đưa đáp án của đề đang thi hoặc đề kiểm tra của lớp.',
  },
  {
    id: 'de-nhap',
    title: 'Đề nháp dùng như thế nào?',
    content: 'Đề nháp không kèm đáp án, để bạn in ra giấy hoặc làm bên ngoài như một đề luyện tập.',
  },
];
