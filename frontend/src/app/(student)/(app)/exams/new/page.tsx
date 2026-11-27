import type { Metadata } from 'next';
import { Suspense } from 'react';
import { CreateExamPage } from '@/features/study/create/create-exam-page';

export const metadata: Metadata = { title: 'Tạo đề với AI' };

export default function Page() {
  return (
    <Suspense>
      <CreateExamPage />
    </Suspense>
  );
}
