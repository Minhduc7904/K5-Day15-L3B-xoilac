'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Alert } from '@/components/ui/feedback';
import { mockMode } from '@/lib/config';
import { authApi } from '../api';
import { prepareGoogleLogin } from '../google-flow';
import { toAuthError } from '../types';

export function GoogleSignIn() {
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string>();

  if (mockMode) return null;

  async function openGoogle() {
    setStarting(true);
    setError(undefined);
    try {
      const challenge = await prepareGoogleLogin();
      const { url } = await authApi.googleStart(challenge);
      window.location.assign(url);
    } catch (failure) {
      setStarting(false);
      setError(toAuthError(failure).message);
    }
  }

  return (
    <div className="grid gap-3">
      <Button type="button" variant="outline" size="lg" fullWidth loading={starting} onClick={openGoogle}>
        Tiếp tục với Google
      </Button>
      {error && <Alert tone="danger" title={error} />}
    </div>
  );
}
