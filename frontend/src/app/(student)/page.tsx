import { LandingPage } from '@/features/landing/landing-page';

// Trang chủ của học sinh. Khách bị `AuthGuard` chuyển tới /login, admin tới /admin.
export default function StudentPage() {
  return <LandingPage />;
}
