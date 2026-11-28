import type { Metadata } from 'next';
import { ImportReviewPage } from '@/features/admin-pdf-imports/components/import-review';

export const metadata: Metadata = { title: 'Duyệt đề PDF · Quản trị' };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <ImportReviewPage id={Number(id)} />;
}
