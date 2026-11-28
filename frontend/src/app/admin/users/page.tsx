import type { Metadata } from 'next';
import { UsersPage } from '@/features/admin-users/components/users-page';

export const metadata: Metadata = { title: 'Người dùng · Quản trị' };

export default function Page() {
  return <UsersPage />;
}
