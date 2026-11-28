import type { Metadata } from 'next';
import { ImportListPage } from '@/features/admin-pdf-imports/components/import-list';

export const metadata: Metadata = { title: 'Nhập đề PDF · Quản trị' };

export default function Page() {
  return <ImportListPage />;
}
