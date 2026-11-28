import type { Metadata } from 'next';
import { TemplateFormPage } from '@/features/admin-exam-templates/components/template-form';

export const metadata: Metadata = { title: 'Sửa mẫu đề · Quản trị' };

export default async function Page({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <TemplateFormPage id={Number(id)} />;
}
