import type { Metadata } from 'next';
import { ExamsListPage } from '@/features/study/exams/exams-list-page';

export const metadata: Metadata = { title: 'Đề của tôi' };

export default function Page() {
  return <ExamsListPage />;
}
