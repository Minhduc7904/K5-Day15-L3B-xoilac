import type { NavLink } from '@/components/layout/navbar';
import { bankChapters, type Grade } from './bank-data';

export const landingLinks: NavLink[] = [
  { href: '#van-de', label: 'Vấn đề' },
  { href: '#cach-hoat-dong', label: 'Cách hoạt động' },
  { href: '#chuc-nang', label: 'Chức năng' },
  { href: '#ngan-hang', label: 'Kho câu hỏi' },
  { href: '#thong-ke', label: 'Thống kê' },
  { href: '#hoi-dap', label: 'Hỏi đáp' },
];

/** Tên chương lấy từ data/chapters.csv, cùng nguồn với số liệu ở bank-data.ts. */
export const chapters: Array<{ grade: Grade; name: string }> = bankChapters.map(({ grade, name }) => ({ grade, name }));

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
