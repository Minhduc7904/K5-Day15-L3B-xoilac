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

export function readGoogleResult() {
  const params = new URLSearchParams(window.location.hash.slice(1));
  const verifier = sessionStorage.getItem(VERIFIER_KEY);
  sessionStorage.removeItem(VERIFIER_KEY);
  window.history.replaceState(null, '', window.location.pathname);
  return { ticket: params.get('ticket'), verifier };
}
