'use client';

import { usePathname, useRouter } from 'next/navigation';
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { Spinner } from '@/components/ui/spinner';
import { mockMode } from '@/lib/config';
import { useAppDispatch, useAppSelector } from '@/store';
import { studentDisplayNameChanged } from '@/features/auth/auth-slice';
import { ErrorState } from '../components/page-states';
import { studentAccountApi, type CreditSummary, type ProfileInput, type ProfileStatus } from './student-account-api';

export const PROFILE_SETUP_PATH = '/profile/setup';

interface StudentAccount {
  status: ProfileStatus | null;
  saveProfile: (input: ProfileInput) => Promise<void>;
  credits: CreditSummary | null;
  creditsError: boolean;
  loadCredits: () => void;
}

const StudentAccountContext = createContext<StudentAccount | null>(null);

export function useStudentAccount() {
  return useContext(StudentAccountContext);
}

function isStudentArea(path: string) {
  return ['/dashboard', '/exams', '/results', '/profile'].some((root) => path === root || path.startsWith(root + '/'));
}

export function StudentAccountProvider({ children }: { children: ReactNode }) {
  const user = useAppSelector((state) => state.auth.user);
  if (mockMode || user?.role !== 'student') return children;

  return <StudentAccountSession key={user.user_id} userId={user.user_id}>{children}</StudentAccountSession>;
}

function StudentAccountSession({ userId, children }: { userId: number; children: ReactNode }) {
  const router = useRouter();
  const path = usePathname();
  const dispatch = useAppDispatch();
  const [status, setStatus] = useState<ProfileStatus | null>(null);
  const [profileError, setProfileError] = useState(false);
  const [profileRequest, setProfileRequest] = useState(0);
  const [credits, setCredits] = useState<CreditSummary | null>(null);
  const [creditsError, setCreditsError] = useState(false);
  const [creditRequest, setCreditRequest] = useState(0);
  const completed = status?.completed === true;

  useEffect(() => {
    const controller = new AbortController();
    studentAccountApi.getProfile(controller.signal).then(
      (result) => { if (!controller.signal.aborted) setStatus(result); },
      () => { if (!controller.signal.aborted) setProfileError(true); },
    );
    return () => controller.abort();
  }, [profileRequest]);

  useEffect(() => {
    if (!completed) return;
    const controller = new AbortController();
    const refresh = () => {
      studentAccountApi.getCredits(undefined, controller.signal).then(
        (result) => {
          if (controller.signal.aborted) return;
          setCredits(result);
          setCreditsError(false);
        },
        () => { if (!controller.signal.aborted) setCreditsError(true); },
      );
    };
    refresh();
    const timer = window.setInterval(refresh, 60_000);
    return () => {
      controller.abort();
      window.clearInterval(timer);
    };
  }, [completed, creditRequest]);

  const inStudentArea = isStudentArea(path);
  const isSetup = path === PROFILE_SETUP_PATH;
  const redirect = inStudentArea && status
    ? completed && isSetup ? '/dashboard' : !completed && !isSetup ? PROFILE_SETUP_PATH : null
    : null;

  useEffect(() => {
    if (redirect) router.replace(redirect);
  }, [redirect, router]);

  if (inStudentArea && profileError && !status) {
    return (
      <div className="grid min-h-dvh place-items-center p-5">
        <ErrorState onRetry={() => { setProfileError(false); setProfileRequest((n) => n + 1); }} />
      </div>
    );
  }
  if (inStudentArea && (!status || redirect)) {
    return <div className="grid min-h-dvh place-items-center"><Spinner label="Đang kiểm tra hồ sơ" /></div>;
  }

  async function saveProfile(input: ProfileInput) {
    const profile = await studentAccountApi.saveProfile(input);
    setStatus({ completed: true, profile, email_verified: profile.email_verified });
    dispatch(studentDisplayNameChanged({ userId, name: profile.display_name }));
  }

  return (
    <StudentAccountContext.Provider value={{
      status, saveProfile, credits, creditsError,
      loadCredits: () => { setCreditsError(false); setCreditRequest((n) => n + 1); },
    }}>
      {children}
    </StudentAccountContext.Provider>
  );
}
