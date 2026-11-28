import type { Metadata } from 'next';
import { Logo } from '@/components/layout/logo';
import { ProfileForm } from '@/features/study/profile/profile-form';

export const metadata: Metadata = { title: 'Hoàn tất hồ sơ' };

export default function Page() {
  return (
    <main className="min-h-dvh bg-surface px-4 py-8 sm:py-12">
      <div className="mx-auto grid max-w-xl gap-5">
        <Logo href="/" className="w-fit" />
        <div className="grid gap-1">
          <h1 className="text-h1 text-foreground">Hoàn tất hồ sơ học sinh</h1>
          <p className="text-body text-muted-foreground">Chọn mục tiêu và lịch ôn luyện của bạn.</p>
        </div>
        <ProfileForm />
      </div>
    </main>
  );
}
