import type { Metadata } from 'next';
import { AdminDashboard } from '@/features/admin-users/components/admin-dashboard';

export const metadata: Metadata = { title: 'Quản trị' };

export default function AdminPage() {
  return <AdminDashboard />;
}
