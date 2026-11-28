'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import { useRealtimeSocket } from '@/features/realtime/realtime-connection';
import { useAppSelector } from '@/store';
import { answerValues, attemptApi, attemptError, AttemptSyncError, type AttemptState, type AttemptUpdate } from '../attempt-api';
import type { Answer } from '../types';

type Pending = { update: AttemptUpdate; queuedAt: number; sent?: boolean };
type Ack = { ok: true; state: AttemptState } | { ok: false; code: string; message: string };

function persisted(prefix: string): Pending[] {
  try {
    return Object.keys(localStorage).filter((key) => key.startsWith(prefix))
      .map((key) => JSON.parse(localStorage.getItem(key)!) as Pending)
      .filter((entry) => entry?.update?.mutation_id)
      .sort((a, b) => a.queuedAt - b.queuedAt);
  } catch {
    return [];
  }
}

function write(prefix: string, item: Pending) {
  try {
    localStorage.setItem(prefix + item.update.mutation_id, JSON.stringify(item));
  } catch {
    // The request can still be saved while this page is open.
  }
}

function remove(prefix: string, id: string) {
  try {
    localStorage.removeItem(prefix + id);
  } catch {
    // Storage may be disabled in the browser.
  }
}

export function useOnlineAttempt(initial: AttemptState | undefined, question: string) {
  const socket = useRealtimeSocket();
  const userId = useAppSelector((store) => store.auth.user?.user_id);
  const id = initial?.attempt_id;
  const prefix = `examind:online:${userId}:${id}:`;
  const stateRef = useRef(initial);
  const [state, setState] = useState(initial);
  const [clock, setClock] = useState(() => ({ now: Date.parse(initial?.server_now ?? ''), local: performance.now() }));
  const [pending, setPending] = useState<Pending[]>([]);
  const [error, setError] = useState<AttemptSyncError | null>(null);
  const [conflict, setConflict] = useState<Pending | null>(null);
  const queue = useRef<Pending[]>([]);
  const inFlight = useRef<Pending | null>(null);
  const draining = useRef<Promise<boolean> | null>(null);
  const conflictRef = useRef<Pending | null>(null);
  const joined = useRef(false);
  const tab = useRef<string | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const activeSegment = useRef<{ question: string; since: number } | null>(null);
  const updateQueue = useCallback((next: Pending[]) => {
    queue.current = next;
    setPending(next);
  }, []);

  const apply = useCallback((next: AttemptState) => {
    if (next.revision < (stateRef.current?.revision ?? 0)) return;
    const now = Date.parse(next.server_now);
    stateRef.current = next;
    setState(next);
    setClock((last) => !Number.isFinite(last.now) || now >= last.now ? { now, local: performance.now() } : last);
  }, []);

  const sync = useCallback(async () => {
    if (id === undefined) return undefined;
    const next = await attemptApi.read(id);
    apply(next);
    return next;
  }, [id, apply]);

  const send = useCallback(async (update: AttemptUpdate) => {
    if (socket?.connected && joined.current) {
      let ack: Ack | undefined;
      try {
        ack = await socket.timeout(1600).emitWithAck('attempt:save', { attempt_id: id, update }) as Ack;
      } catch {
        // Reuse the same mutation ID through HTTP when an acknowledgement is lost.
      }
      if (ack?.ok) return ack.state;
      if (ack && ack.code !== 'ATTEMPT_ROOM_REQUIRED') throw new AttemptSyncError(ack.code, ack.message);
    }
    return attemptApi.save(id!, update);
  }, [id, socket]);

  const flush = useCallback((): Promise<boolean> => {
    if (id === undefined) return Promise.resolve(true);
    if (draining.current) return draining.current;
    if (conflictRef.current) return Promise.resolve(false);
    const run = async () => {
      setError(null);
      while (queue.current.length && !conflictRef.current && stateRef.current?.status === 'in_progress') {
        const item = queue.current[0];
        inFlight.current = item;
        item.sent = true;
        write(prefix, item);
        try {
          apply(await send(item.update));
          remove(prefix, item.update.mutation_id);
          updateQueue(queue.current.filter((entry) => entry !== item));
        } catch (failure) {
          const problem = attemptError(failure);
          setError(problem);
          if (problem.code === 'ANSWER_CONFLICT') {
            conflictRef.current = item;
            setConflict(item);
          }
          if (problem.code === 'ANSWER_CONFLICT' || problem.code === 'ATTEMPT_FINISHED') {
            await sync().catch(() => undefined);
          }
          return false;
        } finally {
          inFlight.current = null;
        }
      }
      return queue.current.length === 0;
    };
    const promise = run().finally(() => { draining.current = null; });
    draining.current = promise;
    return promise;
  }, [id, apply, send, prefix, sync, updateQueue]);

  const enqueue = useCallback((update: AttemptUpdate) => {
    const entry = { update, queuedAt: performance.timeOrigin + performance.now() };
    write(prefix, entry);
    updateQueue([...queue.current, entry]);
  }, [prefix, updateQueue]);

  useEffect(() => {
    if (id === undefined || userId === undefined) return;
    updateQueue(persisted(prefix));
  }, [id, userId, prefix, updateQueue]);

  useEffect(() => {
    if (id === undefined) return;
    const refresh = () => { void sync().then(() => flush(), () => undefined); };
    const visible = () => { if (document.visibilityState === 'visible') refresh(); };
    const join = async () => {
      if (!socket?.connected) return;
      try {
        const ack = await socket.timeout(2200).emitWithAck('attempt:join', { attempt_id: id }) as Ack;
        if (ack.ok) {
          joined.current = true;
          apply(ack.state);
          void flush();
        }
      } catch {
        refresh();
      }
    };
    const disconnected = () => { joined.current = false; };
    const changed = (event: { attempt_id: number; revision: number }) => {
      if (event.attempt_id === id && event.revision > (stateRef.current?.revision ?? 0)) {
        void sync().catch(() => undefined);
      }
    };
    socket?.on('connect', join);
    socket?.on('disconnect', disconnected);
    socket?.on('attempt:updated', changed);
    socket?.on('attempt:finished', changed);
    window.addEventListener('online', refresh);
    document.addEventListener('visibilitychange', visible);
    const poll = window.setInterval(() => {
      if (!joined.current && document.visibilityState === 'visible') refresh();
    }, 6000);
    if (socket?.connected) void join();
    else refresh();
    return () => {
      joined.current = false;
      socket?.off('connect', join);
      socket?.off('disconnect', disconnected);
      socket?.off('attempt:updated', changed);
      socket?.off('attempt:finished', changed);
      if (socket?.connected) socket.emit('attempt:leave', { attempt_id: id });
      window.removeEventListener('online', refresh);
      document.removeEventListener('visibilitychange', visible);
      window.clearInterval(poll);
    };
  }, [id, socket, sync, apply, flush]);

  const change = useCallback((code: string, answer: Answer | ((value: Answer) => Answer), debounce: boolean) => {
    if (stateRef.current?.status !== 'in_progress') return;
    const previous = queue.current.findLast(({ update }) => update.question === code && update.base_revision !== undefined);
    const server = stateRef.current.answers[code];
    const replace = previous && !previous.sent && inFlight.current !== previous && conflictRef.current !== previous;
    if (replace) {
      remove(prefix, previous.update.mutation_id);
      updateQueue(queue.current.filter((entry) => entry !== previous));
    }
    const current = previous ? previous.update.answer ?? null : server?.value ?? null;
    const revision = previous ? previous.update.base_revision! + (replace ? 0 : 1) : server?.revision ?? 0;
    enqueue({ question: code, answer: typeof answer === 'function' ? answer(current) : answer,
      base_revision: revision, mutation_id: crypto.randomUUID() });
    window.clearTimeout(timer.current);
    if (debounce) timer.current = window.setTimeout(() => void flush(), 500);
    else void flush();
  }, [enqueue, flush, prefix, updateQueue]);

  const resolveConflict = useCallback(async (applyMine: boolean) => {
    const blocked = conflictRef.current;
    if (!blocked) return;
    try {
      const latest = await sync();
      if (!latest || latest.status !== 'in_progress') return;
      const sameQuestion = queue.current.filter(({ update }) =>
        update.question === blocked.update.question && update.base_revision !== undefined);
      const last = sameQuestion.at(-1) ?? blocked;
      sameQuestion.forEach(({ update }) => remove(prefix, update.mutation_id));
      updateQueue(queue.current.filter((item) => !sameQuestion.includes(item)));
      conflictRef.current = null;
      setConflict(null);
      if (applyMine) enqueue({ ...last.update, mutation_id: crypto.randomUUID(),
        base_revision: latest.answers[blocked.update.question]?.revision ?? 0 });
      void flush();
    } catch (failure) {
      setError(attemptError(failure));
    }
  }, [enqueue, flush, prefix, sync, updateQueue]);

  const checkpoint = useCallback((nextQuestion: string, release = false, keepalive = false) => {
    if (id === undefined || !nextQuestion || stateRef.current?.status !== 'in_progress') return;
    if (stateRef.current.deadline_at && Number.isFinite(clock.now)
      && Date.parse(stateRef.current.deadline_at) <= clock.now + performance.now() - clock.local) return;
    tab.current ??= crypto.randomUUID();
    const now = performance.now();
    const segment = activeSegment.current;
    const elapsed = segment ? Math.min(6000, Math.max(0, Math.floor(now - segment.since))) : 0;
    activeSegment.current = release ? null : { question: nextQuestion, since: now };
    // Offline time is approximate. Keep unsent answer edits and bound queued checkpoints.
    if (queue.current.filter(({ update }) => update.tab_id).length >= 6) return;
    const update = { mutation_id: crypto.randomUUID(), question: segment?.question ?? nextQuestion,
      current: nextQuestion, tab_id: tab.current, elapsed_ms: elapsed, release_tab: release };
    enqueue(update);
    if (keepalive && queue.current.length === 1) {
      void fetch(`/api/v1/study/attempts/${id}`, { method: 'PATCH', keepalive: true, credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(update) }).catch(() => undefined);
      return;
    }
    void flush();
  }, [id, clock, enqueue, flush]);

  const checkpointRef = useRef(checkpoint);
  useEffect(() => { checkpointRef.current = checkpoint; }, [checkpoint]);
  useEffect(() => {
    if (id === undefined || !question || !state || state.status === 'graded') return;
    const visible = () => document.visibilityState === 'visible' && document.hasFocus();
    const track = () => {
      if (visible()) checkpointRef.current(question);
      else if (activeSegment.current) checkpointRef.current(question, true);
    };
    const leave = () => { if (activeSegment.current) checkpointRef.current(question, true, true); };
    track();
    const interval = window.setInterval(track, 4000);
    window.addEventListener('focus', track);
    window.addEventListener('blur', track);
    window.addEventListener('pagehide', leave);
    document.addEventListener('visibilitychange', track);
    return () => {
      window.clearInterval(interval);
      window.removeEventListener('focus', track);
      window.removeEventListener('blur', track);
      window.removeEventListener('pagehide', leave);
      document.removeEventListener('visibilitychange', track);
    };
  }, [id, question, state?.status]); // The state revision changes after every checkpoint.

  const answers = state ? answerValues(state) : {};
  for (const { update } of pending) {
    if (update.base_revision !== undefined) answers[update.question] = update.answer ?? null;
  }
  function clearPending() {
    queue.current.forEach(({ update }) => remove(prefix, update.mutation_id));
    updateQueue([]);
  }

  return { state, clock, answers, error, conflict, resolveConflict, change, checkpoint, flush, sync, apply, clearPending,
    pendingAnswers: pending.filter(({ update }) => update.base_revision !== undefined).length };
}
