import { LandingPage } from '@/features/landing/landing-page';

// Khách vào `/` thấy landing. Khi có phiên đăng nhập thật (#8), học sinh đã đăng nhập sẽ được chuyển vào khu học tập.
export default function StudentPage() {
  return <LandingPage />;
}
