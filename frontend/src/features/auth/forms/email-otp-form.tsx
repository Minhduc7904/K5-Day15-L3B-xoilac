'use client';

import { MailCheck } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Alert } from '@/components/ui/feedback';
import { OtpInput } from '@/components/ui/otp-input';
import { useToast } from '@/components/ui/toast';
import { useAppDispatch } from '@/store';
import { authApi } from '../api';
import { signedIn } from '../auth-slice';
import { homeFor } from '../route-guard';
import { AuthHeader } from '../components/auth-shell';
import { toAuthError, type OtpPurpose, type PendingOtp } from '../types';
import { maskEmail } from '../validation';

export function EmailOtpForm({
  initial,
  purpose,
  onBack,
}: {
  initial: PendingOtp;
  purpose: OtpPurpose;
  onBack: () => void;
}) {
  const router = useRouter();
  const dispatch = useAppDispatch();
  const toast = useToast();
  const [pending, setPending] = useState(initial);
  const [code, setCode] = useState('');
  const [error, setError] = useState<ReturnType<typeof toAuthError>>();
  const [operation, setOperation] = useState<'verify' | 'resend'>();
  const [countdown, setCountdown] = useState(initial.resend_after);

  useEffect(() => {
    const availableAt = Date.now() + pending.resend_after * 1000;
    const timer = window.setInterval(
      () => setCountdown(Math.max(0, Math.ceil((availableAt - Date.now()) / 1000))),
      500,
    );
    return () => window.clearInterval(timer);
  }, [pending]);

  async function complete() {
    if (operation || code.length !== 6) return;
    setOperation('verify');
    setError(undefined);
    try {
      const user = await authApi.completeOtp(purpose, pending.challenge, code);
      dispatch(signedIn(user));
      toast({ tone: 'success', title: 'Đã xác minh email' });
      router.replace(homeFor(user));
    } catch (failure) {
      setError(toAuthError(failure));
      setCode('');
    } finally {
      setOperation(undefined);
    }
  }

  async function resend() {
    if (operation || countdown > 0) return;
    setOperation('resend');
    setError(undefined);
    try {
      const next = await authApi.resendOtp(purpose, pending.challenge);
      setPending(next);
      setCountdown(next.resend_after);
      setCode('');
      toast({ tone: 'success', title: 'Đã gửi mã mới' });
    } catch (failure) {
      setError(toAuthError(failure));
    } finally {
      setOperation(undefined);
    }
  }

  return (
    <div className="grid gap-6">
      <AuthHeader
        icon={<MailCheck />}
        mascot="working"
        title="Xác minh email"
        description={`Nhập mã 6 số gửi tới ${maskEmail(pending.email)}. Mã có hiệu lực ${Math.ceil(pending.expires_in / 60)} phút.`}
      />
      {error && <Alert tone="danger" title={error.message} />}
      <form
        className="grid gap-4"
        onSubmit={(event) => {
          event.preventDefault();
          void complete();
        }}
      >
        <OtpInput
          length={6}
          label="Mã xác minh email"
          value={code}
          onChange={setCode}
          invalid={error?.code === 'OTP_INVALID'}
          disabled={Boolean(operation)}
          autoFocus
        />
        <Button type="submit" size="lg" fullWidth loading={operation === 'verify'} disabled={code.length !== 6 || Boolean(operation)}>
          Xác minh email
        </Button>
      </form>
      <div className="flex flex-wrap justify-center gap-2">
        <Button variant="secondary" disabled={countdown > 0 || Boolean(operation)} loading={operation === 'resend'} onClick={resend}>
          {countdown > 0 ? `Gửi lại sau ${countdown}s` : 'Gửi lại mã'}
        </Button>
        <Button variant="ghost" disabled={Boolean(operation)} onClick={onBack}>Quay lại</Button>
      </div>
    </div>
  );
}
