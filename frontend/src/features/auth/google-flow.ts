const VERIFIER_KEY = 'examind:google-verifier';

function base64Url(bytes: Uint8Array<ArrayBuffer>) {
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

export async function prepareGoogleLogin() {
  const verifier = base64Url(crypto.getRandomValues(new Uint8Array(32)));
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
  sessionStorage.setItem(VERIFIER_KEY, verifier);
  return base64Url(new Uint8Array(digest));
}

/**
 * Đọc kết quả backend gắn trên hash (`#ticket=...` hoặc `#error=google`) và verifier của tab.
 * Chỉ đọc được một lần: hash và verifier bị xoá ngay.
 */
export function readGoogleResult() {
  const params = new URLSearchParams(window.location.hash.slice(1));
  const verifier = sessionStorage.getItem(VERIFIER_KEY);
  sessionStorage.removeItem(VERIFIER_KEY);
  window.history.replaceState(null, '', window.location.pathname);
  return { ticket: params.get('ticket'), error: params.get('error'), verifier };
}

/** Lý do không đổi được ticket thành phiên, để báo đúng cho người dùng. */
export type GoogleResultProblem = 'provider' | 'other-origin' | 'missing';

export function googleResultProblem(result: ReturnType<typeof readGoogleResult>): GoogleResultProblem | null {
  if (result.error) return 'provider';
  if (!result.ticket) return 'missing';
  if (!result.verifier) return 'other-origin';
  return null;
}
