import type { Metadata } from 'next';
import { ProfilePage } from '@/features/study/profile/profile-page';

export const metadata: Metadata = { title: 'Hồ sơ' };

export default function Page() {
  return <ProfilePage />;
}
