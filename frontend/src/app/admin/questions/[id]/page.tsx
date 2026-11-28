import type { Metadata } from 'next';
import { QuestionDetailPage } from '@/features/admin-questions/components/question-detail';

export const metadata: Metadata = { title: 'Chi tiết câu hỏi · Quản trị' };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <QuestionDetailPage id={Number(id)} />;
}
