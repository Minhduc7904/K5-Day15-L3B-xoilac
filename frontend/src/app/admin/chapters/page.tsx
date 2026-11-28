import type { Metadata } from 'next';
import { ChapterTreePage } from '@/features/admin-chapters/components/chapter-tree-page';

export const metadata: Metadata = { title: 'Chương · Quản trị' };

export default function Page() {
  return <ChapterTreePage />;
}
