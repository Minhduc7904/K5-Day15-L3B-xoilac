import type { Metadata } from 'next';
import { Suspense } from 'react';
import { LiveCreateExamPage } from '@/features/study/create/live-create-exam-page';

export const metadata: Metadata = { title: 'Tạo đề với AI' };

export default function Page() {
  return (
    <Suspense>
      <LiveCreateExamPage />
    </Suspense>
  );
}
