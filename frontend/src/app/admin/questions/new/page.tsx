import type { Metadata } from 'next';
import { QuestionFormPage } from '@/features/admin-questions/components/question-form';

export const metadata: Metadata = { title: 'Thêm câu hỏi · Quản trị' };

export default function Page() {
  return <QuestionFormPage />;
}
