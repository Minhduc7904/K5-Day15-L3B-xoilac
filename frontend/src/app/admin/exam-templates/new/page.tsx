import type { Metadata } from 'next';
import { TemplateFormPage } from '@/features/admin-exam-templates/components/template-form';

export const metadata: Metadata = { title: 'Thêm mẫu đề · Quản trị' };

export default function Page() {
  return <TemplateFormPage />;
}
