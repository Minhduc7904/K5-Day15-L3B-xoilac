import type { Metadata } from 'next';
import { ExamDetailPage } from '@/features/study/exams/exam-detail-page';

export const metadata: Metadata = { title: 'Chi tiết đề' };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ExamDetailPage id={id} />;
}
