import type { Metadata } from 'next';
import { AdminDashboard } from '@/features/admin/admin-dashboard';

export const metadata: Metadata = { title: 'Quản trị' };

export default function AdminPage() {
  return <AdminDashboard />;
}
