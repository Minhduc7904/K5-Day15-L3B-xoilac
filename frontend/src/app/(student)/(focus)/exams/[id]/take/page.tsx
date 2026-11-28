import type { Metadata } from 'next';
import { TakeExamPage } from '@/features/study/take/take-exam-page';

export const metadata: Metadata = { title: 'Làm bài' };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <TakeExamPage id={id} />;
}
