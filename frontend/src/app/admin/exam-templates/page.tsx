import type { Metadata } from 'next';
import { TemplateListPage } from '@/features/admin-exam-templates/components/template-list';

export const metadata: Metadata = { title: 'Mẫu cấu trúc đề · Quản trị' };

export default function Page() {
  return <TemplateListPage />;
}
