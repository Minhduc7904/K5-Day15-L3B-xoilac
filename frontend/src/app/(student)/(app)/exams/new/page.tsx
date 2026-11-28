import type { Metadata } from 'next';
import { Suspense } from 'react';
import { liveExamChat } from '@/lib/config';
import { LiveCreateExamPage } from '@/features/study/create/live-create-exam-page';
import { CreateExamPage } from '@/features/study/create/create-exam-page';

export const metadata: Metadata = { title: 'Tạo đề với AI' };

export default function Page() {
  return (
    <Suspense>
      {liveExamChat ? <LiveCreateExamPage /> : <CreateExamPage />}
    </Suspense>
  );
}
