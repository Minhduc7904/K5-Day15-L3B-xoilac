'use client';

import { MailCheck, RotateCcw } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Alert, Skeleton } from '@/components/ui/feedback';
import { OtpInput } from '@/components/ui/otp-input';
import { useToast } from '@/components/ui/toast';
import { authApi } from '../api';
import { AuthHeader, TextLink } from '../components/auth-shell';
import { readResetFlow, writeResetFlow, type ResetFlow } from '../reset-flow';
import { toAuthError } from '../types';
import { maskEmail } from '../validation';

const OTP_LENGTH = 6;
const RESEND_SECONDS = 60;

type Problem = { kind: 'invalid'; remaining?: number } | { kind: 'expired' } | { kind: 'locked' } | { kind: 'network' };

function secondsLeft(sentAt: number) {
  return Math.max(0, RESEND_SECONDS - Math.floor((Date.now() - sentAt) / 1000));
}

export function VerifyOtpForm() {
  const router = useRouter();
  const toast = useToast();
  const [flow, setFlow] = useState<ResetFlow | null | undefined>(undefined);
  const [code, setCode] = useState('');
  const [problem, setProblem] = useState<Problem | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [resending, setResending] = useState(false);
  const [countdown, setCountdown] = useState(0);
  const [shakeKey, setShakeKey] = useState(0);

  useEffect(() => {
    const current = readResetFlow();
    setFlow(current);
    if (current) setCountdown(secondsLeft(current.sentAt));
  }, []);

  useEffect(() => {
    if (countdown <= 0) return;
    const timer = window.setTimeout(() => setCountdown((c) => c - 1), 1000);
    return () => window.clearTimeout(timer);
  }, [countdown]);

  const verify = async (value: string) => {
    if (!flow || verifying || problem?.kind === 'locked') return;
    if (!/^\d{6}$/.test(value)) {
      setProblem({ kind: 'invalid' });
      setShakeKey((k) => k + 1);
      return;
    }
    setVerifying(true);
    setProblem(null);
    try {
      const { reset_token } = await authApi.verifyOtp(flow.email, value);
      writeResetFlow({ ...flow, resetToken: reset_token });
      toast({ tone: 'success', title: 'Xác minh thành công', description: 'Giờ bạn đặt mật khẩu mới nhé.' });
      router.push('/reset-password');
    } catch (error) {
      const authError = toAuthError(error);
      setCode('');
      setShakeKey((k) => k + 1);
      if (authError.code === 'OTP_INVALID') setProblem({ kind: 'invalid', remaining: authError.remainingAttempts });
      else if (authError.code === 'OTP_EXPIRED') setProblem({ kind: 'expired' });
      else if (authError.code === 'TOO_MANY_ATTEMPTS') setProblem({ kind: 'locked' });
      else setProblem({ kind: 'network' });
    } finally {
      setVerifying(false);
    }
  };

  const resend = async () => {
    if (!flow) return;
    setResending(true);
    try {
      await authApi.forgotPassword(flow.email);
      const next = { email: flow.email, sentAt: Date.now() };
      writeResetFlow(next);
      setFlow(next);
      setCountdown(RESEND_SECONDS);
      setProblem(null);
      setCode('');
      toast({
        tone: 'success',
        title: 'Đã gửi mã mới',
        description: `Mã mới đã gửi tới ${maskEmail(flow.email)}.`,
      });
    } catch (error) {
      const authError = toAuthError(error);
      // Gửi lại quá sớm hoặc quá nhiều lần: báo nội dung từ máy chủ thay vì lỗi mạng.
      if (authError.code === 'OTP_RESEND_LIMIT' || authError.code === 'EMAIL_UNAVAILABLE') {
        toast({ tone: 'danger', title: 'Chưa gửi được mã mới', description: authError.message });
      } else setProblem({ kind: 'network' });
    } finally {
      setResending(false);
    }
  };

  if (flow === undefined) {
    return (
      <div className="grid gap-4" aria-hidden="true">
        <Skeleton className="h-10 w-2/3" />
        <Skeleton className="h-5 w-full" />
        <Skeleton className="h-16 w-full" />
      </div>
    );
  }

  if (!flow) {
    return (
      <div className="grid gap-7">
        <AuthHeader icon={<MailCheck />} mascot="studying" title="Nhập mã xác minh" description="Bạn cần yêu cầu mã trước đã." />
        <Alert
          tone="warning"
          title="Chưa có yêu cầu đặt lại mật khẩu"
          action={
            <Button size="sm" href="/forgot-password">
              Gửi mã xác minh
            </Button>
          }
        >
          Có thể bạn đã mở trang này ở tab khác hoặc yêu cầu đã kết thúc.
        </Alert>
      </div>
    );
  }

  const locked = problem?.kind === 'locked';
  const errorText =
    problem?.kind === 'invalid'
      ? problem.remaining !== undefined
        ? `Mã chưa đúng. Bạn còn ${problem.remaining} lần thử.`
        : 'Bạn nhập đủ 6 chữ số nhé.'
      : problem?.kind === 'expired'
        ? 'Mã đã hết hạn. Bấm "Gửi lại mã" để nhận mã mới.'
        : undefined;

  return (
    <div className="grid gap-7">
      <AuthHeader
        icon={<MailCheck />}
        mascot="working"
        title="Nhập mã xác minh"
        description={
          <>
            Mình đã gửi mã 6 số tới <strong className="font-semibold text-foreground">{maskEmail(flow.email)}</strong>.
            Mã có hiệu lực trong 5 phút.
          </>
        }
      />

      {locked && (
        <Alert tone="danger" title="Bạn đã nhập sai quá nhiều lần">
          Mã này đã bị khoá để bảo vệ tài khoản. Bấm &quot;Gửi lại mã&quot; để nhận mã mới.
        </Alert>
      )}
      {problem?.kind === 'network' && (
        <Alert tone="danger" title="Không kết nối được máy chủ">
          Kiểm tra mạng rồi thử lại nhé.
        </Alert>
      )}

      <form
        noValidate
        onSubmit={(e) => {
          e.preventDefault();
          void verify(code.replace(/\s/g, ''));
        }}
        className="grid gap-5"
      >
        <div className="grid gap-2">
          <OtpInput
            label="Mã xác minh 6 chữ số"
            length={OTP_LENGTH}
            value={code}
            onChange={(v) => {
              setCode(v);
              if (problem?.kind === 'invalid' || problem?.kind === 'expired') setProblem(null);
            }}
            onComplete={(v) => void verify(v)}
            invalid={Boolean(errorText)}
            disabled={verifying || locked}
            shakeKey={shakeKey}
            autoFocus
            aria-describedby={errorText ? 'otp-error' : undefined}
          />
          <p
            id="otp-error"
            role={errorText ? 'alert' : undefined}
            className="min-h-5 text-center text-caption font-medium text-danger"
          >
            {errorText}
          </p>
        </div>

        <Button type="submit" size="lg" fullWidth loading={verifying} disabled={locked}>
          {verifying ? 'Đang xác minh…' : 'Xác minh'}
        </Button>
      </form>

      <div className="grid justify-items-center gap-2 text-center">
        {countdown > 0 && !locked && problem?.kind !== 'expired' ? (
          <p className="text-body text-muted-foreground" aria-live="off">
            Chưa nhận được mã? Gửi lại sau{' '}
            <span className="font-semibold text-foreground tabular-nums">
              0:{String(countdown).padStart(2, '0')}
            </span>
          </p>
        ) : (
          <Button variant="secondary" onClick={resend} loading={resending} leftIcon={<RotateCcw aria-hidden="true" />}>
            Gửi lại mã
          </Button>
        )}
        <TextLink href="/forgot-password">Đổi email khác</TextLink>
      </div>
    </div>
  );
}
