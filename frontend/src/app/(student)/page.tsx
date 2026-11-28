import { LandingPage } from '@/features/landing/landing-page';

// Trang chủ: khách và học sinh đều xem được; admin bị `AuthGuard` chuyển tới /admin.
export default function StudentPage() {
  return <LandingPage />;
}
