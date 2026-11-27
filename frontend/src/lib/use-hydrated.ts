'use client';

import { useSyncExternalStore } from 'react';

const subscribe = () => () => {};

/**
 * `false` khi render trên server và trong lúc hydrate, `true` sau đó.
 * Dùng cho UI phụ thuộc state chỉ có ở client (vd user do splash nạp vào store),
 * để HTML lúc hydrate khớp với server.
 */
export function useHydrated() {
  return useSyncExternalStore(
    subscribe,
    () => true,
    () => false,
  );
}
