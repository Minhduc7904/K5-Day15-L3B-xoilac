import type { Metadata } from 'next';
import { QuestionFormPage } from '@/features/admin-questions/components/question-form';

export const metadata: Metadata = { title: 'Sửa câu hỏi · Quản trị' };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <QuestionFormPage id={Number(id)} />;
}
