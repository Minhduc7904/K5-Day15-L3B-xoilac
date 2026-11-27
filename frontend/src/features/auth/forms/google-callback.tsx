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
import { readGoogleResult } from '../google-flow';
import { toAuthError, type PendingOtp } from '../types';
import { EmailOtpForm } from './email-otp-form';

export function GoogleCallback() {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const started = useRef(false);
  const [pending, setPending] = useState<PendingOtp>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    async function finish() {
      try {
        const { ticket, verifier } = readGoogleResult();
        if (!ticket || !verifier) {
          setError('Phiên đăng nhập Google đã kết thúc. Hãy đăng nhập lại.');
          return;
        }
        const result = await authApi.googleExchange(ticket, verifier);
        if ('challenge' in result) {
          setPending(result);
        } else {
          dispatch(signedIn(result));
          router.replace('/');
        }
      } catch (failure) {
        setError(toAuthError(failure).message);
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
          <Alert tone="danger" title={error} />
          <Button href="/login">Về trang đăng nhập</Button>
        </>
      )}
    </div>
  );
}
