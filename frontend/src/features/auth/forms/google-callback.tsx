'use client';

import { LogIn } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Alert } from '@/components/ui/feedback';
import { useAppDispatch } from '@/store';
import { authApi } from '../api';
import { signedIn } from '../auth-slice';
import { AuthHeader } from '../components/auth-shell';
import { googleResultProblem, readGoogleResult, type GoogleResultProblem } from '../google-flow';
import { toAuthError, type PendingOtp } from '../types';
import { EmailOtpForm } from './email-otp-form';

const PROBLEMS: Record<GoogleResultProblem, { title: string; body: string }> = {
  provider: {
    title: 'Google chưa xác minh được tài khoản',
    body: 'Có thể bạn đã huỷ ở bước chọn tài khoản hoặc yêu cầu đã quá hạn. Hãy thử đăng nhập Google lại.',
  },
  'other-origin': {
    title: 'Không tìm thấy yêu cầu đăng nhập trong tab này',
    body: `Bạn cần bắt đầu và hoàn tất đăng nhập Google trên cùng một trang và cùng một tab. Hãy bấm "Đăng nhập Google" lại tại ${typeof window === 'undefined' ? 'trang này' : window.location.host}.`,
  },
  missing: {
    title: 'Liên kết đăng nhập Google đã được dùng',
    body: 'Trang này chỉ dùng được một lần ngay sau khi Google chuyển về, nên tải lại trang sẽ không đăng nhập được. Hãy đăng nhập lại.',
  },
};

export function GoogleCallback() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const started = useRef(false);
  const [pending, setPending] = useState<PendingOtp>();
  const [error, setError] = useState<{ title: string; body?: string }>();

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    async function finish() {
      try {
        const read = readGoogleResult();
        const problem = googleResultProblem(read);
        if (problem || !read.ticket || !read.verifier) {
          setError(PROBLEMS[problem ?? 'missing']);
          return;
        }
        const result = await authApi.googleExchange(read.ticket, read.verifier);
        if ('challenge' in result) {
          setPending(result);
        } else {
          dispatch(signedIn(result));
          router.replace('/');
        }
      } catch (failure) {
        setError({ title: toAuthError(failure).message });
      }
    }

    void finish();
  }, [dispatch, router]);

  if (pending) {
    return <EmailOtpForm initial={pending} purpose="google_email" onBack={() => router.replace('/login')} />;
  }

  return (
    <div className="grid gap-5">
      <AuthHeader
        icon={<LogIn />}
        mascot="working"
        title="Đăng nhập Google"
        description={error ? undefined : 'Đang xác minh tài khoản của bạn…'}
      />
      {error && (
        <>
          <Alert tone="danger" title={error.title}>
            {error.body}
          </Alert>
          <Button href="/login">Về trang đăng nhập</Button>
        </>
      )}
    </div>
  );
}
