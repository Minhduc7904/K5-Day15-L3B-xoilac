import type { Metadata } from 'next';
import { ResultPage } from '@/features/study/result/result-page';

export const metadata: Metadata = { title: 'Kết quả' };

export default async function Page({ params }: { params: Promise<{ attemptId: string }> }) {
  const { attemptId } = await params;
  return <ResultPage attemptId={attemptId} />;
}
