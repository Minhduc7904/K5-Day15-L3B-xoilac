import type { Metadata } from 'next';
import { Suspense } from 'react';
import { QuestionListPage } from '@/features/admin-questions/components/question-list';

export const metadata: Metadata = { title: 'Câu hỏi · Quản trị' };

export default function Page() {
  return (
    <Suspense>
      <QuestionListPage />
    </Suspense>
  );
}
