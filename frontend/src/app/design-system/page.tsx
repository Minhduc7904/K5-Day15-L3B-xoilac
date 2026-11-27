import type { Metadata } from 'next';
import { notFound } from 'next/navigation';
import { DesignSystemShowcase } from '@/features/design-system/showcase';
import { mockMode } from '@/lib/config';

export const metadata: Metadata = { title: 'Design system', robots: { index: false } };

// Chỉ bật ở môi trường dev hoặc chế độ mock.
export default function DesignSystemPage() {
  if (process.env.NODE_ENV === 'production' && !mockMode) notFound();
  return <DesignSystemShowcase />;
}
