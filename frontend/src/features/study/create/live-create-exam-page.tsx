'use client';

import { useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/toast';
import {
  chatAttachmentUrl, defaultPointWeights, draftLink, examChatApi, examChatError, type PointWeights, type ServerDraft, type ServerMessage,
  type ServerPreview, type ServerSession,
} from '../exam-chat-api';
import { difficultyLabels, typeLabels } from '../fixtures/chapters';
import { useStudentAccount } from '../profile/student-account-provider';
import type { StructureRow } from '../types';
import { addImages, Composer, EXAM_CHAT_IMAGES, type Attachment } from './composer';

const field = 'min-w-0 rounded-lg border border-border bg-background px-2 py-2 text-label text-foreground';
const starter = ['Ôn theo mẫu kỳ thi trong hồ sơ của mình', 'Ra 20 câu nguyên hàm và tích phân'];
const DIFFICULTIES = Object.keys(difficultyLabels) as StructureRow['difficulty'][];
const TYPES = Object.keys(defaultPointWeights) as Array<keyof PointWeights>;

export function LiveCreateExamPage() {
  const params = useSearchParams();
  const account = useStudentAccount();
  const toast = useToast();
  const [sessions, setSessions] = useState<ServerSession[]>([]);
  const [catalog, setCatalog] = useState<Record<string, string>>({});
  const [active, setActive] = useState<number | null>(null);
  const [messages, setMessages] = useState<ServerMessage[]>([]);
  const [preview, setPreview] = useState<ServerPreview | null>(null);
  const [draft, setDraft] = useState<ServerDraft | null>(null);
  const [reply, setReply] = useState('');
  const [pendingText, setPendingText] = useState('');
  const [attachments, setAttachments] = useState<Attachment[]>([]);
  const [pendingImages, setPendingImages] = useState<Attachment[]>([]);
  const [busy, setBusy] = useState(false);
  const [initializing, setInitializing] = useState(true);
  const [hasOlder, setHasOlder] = useState(false);
  const [error, setError] = useState('');
  const [retryText, setRetryText] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const locked = useRef(false);
  const started = useRef(false);
  const scroll = useRef<HTMLDivElement>(null);
  const shownImages = useRef<Attachment[]>([]);
  const resetImages = useCallback(() => {
    for (const image of shownImages.current) URL.revokeObjectURL(image.url);
    shownImages.current = [];
    setAttachments([]);
    setPendingImages([]);
  }, []);
  useEffect(() => {
    shownImages.current = [...attachments, ...pendingImages];
  }, [attachments, pendingImages]);
  useEffect(() => () => {
    for (const image of shownImages.current) URL.revokeObjectURL(image.url);
  }, []);

  const refresh = useCallback(async (id: number) => {
    const state = await examChatApi.state(id);
    setMessages(state.messages);
    setHasOlder(state.messages.length === 200);
    setPreview(state.preview);
    setDraft(state.draft);
  }, []);

  const select = useCallback(async (id: number) => {
    if (locked.current) return;
    locked.current = true;
    setBusy(true);
    setError('');
    setRetryText(null);
    resetImages();
    setEditing(false);
    try {
      await refresh(id);
      setActive(id);
      window.history.replaceState(null, '', '/exams/new?session=' + id);
    } catch (cause) {
      setError(examChatError(cause));
    } finally {
      locked.current = false;
      setBusy(false);
    }
  }, [refresh, resetImages]);

  const initialize = useCallback(async () => {
    setInitializing(true);
    setError('');
    try {
      const [saved, names] = await Promise.all([examChatApi.sessions(), examChatApi.chapters()]);
      setSessions(saved);
      setCatalog(Object.fromEntries(Object.entries(names).map(([code, item]) => [
        code, item.parent_code && names[item.parent_code]
          ? names[item.parent_code].name + ' / ' + item.name : item.name,
      ])));
      const id = Number(new URLSearchParams(window.location.search).get('session'));
      if (id) await select(id);
    } catch (cause) {
      setError(examChatError(cause));
    } finally {
      setInitializing(false);
    }
  }, [select]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void initialize();
  }, [initialize]);

  useEffect(() => {
    if (scroll.current) scroll.current.scrollTop = scroll.current.scrollHeight;
  }, [active, pendingText, pendingImages, reply]);

  const clear = () => {
    if (locked.current) return;
    setActive(null);
    setMessages([]);
    setPreview(null);
    setDraft(null);
    setEditing(false);
    setError('');
    setRetryText(null);
    resetImages();
    setHasOlder(false);
    window.history.replaceState(null, '', '/exams/new');
  };

  const send = useCallback(async (text: string, images: Attachment[] = []) => {
    if ((!text.trim() && !images.length) || locked.current) return;
    locked.current = true;
    let id = active;
    setBusy(true);
    setError('');
    setRetryText(null);
    setPendingText(text);
    if (images.length) {
      setAttachments([]);
      setPendingImages(images);
    }
    let sent = false;
    try {
      if (id === null) {
        const session = await examChatApi.create();
        id = session.session_id;
        setActive(id);
        setSessions((list) => [{ ...session, title: text.slice(0, 80) || 'Ảnh đã gửi' }, ...list]);
        window.history.replaceState(null, '', '/exams/new?session=' + id);
      }
      for await (const event of examChatApi.send(id, text, preview?.version ?? 0, images.map((item) => item.file))) {
        if (event.event === 'error') throw new Error(event.data.message);
        if (event.event === 'message') setReply((previous) => previous + event.data.delta);
        if (event.event === 'preview') {
          setEditing(false);
          setPreview(event.data);
        }
        if (event.event === 'draft') {
          setDraft(event.data);
          account?.loadCredits();
        }
        if (event.event === 'done') sent = true;
      }
      await refresh(id);
      setSessions(await examChatApi.sessions());
    } catch (cause) {
      const state = id === null ? null : await examChatApi.state(id).catch(() => null);
      if (state) {
        setMessages(state.messages);
        setPreview(state.preview);
        setDraft(state.draft);
        if (state.draft) account?.loadCredits();
        sent ||= state.messages.some((item) => item.role === 'student' && item.content === text && (item.attachments?.length ?? 0) === images.length
          && !messages.some((known) => known.message_id === item.message_id));
      }
      if (!sent) {
        setError(examChatError(cause));
        setRetryText(text);
        if (images.length) setAttachments(images);
      } else if (!state) {
        setError('Tin nhắn đã được gửi. Tải lại phiên để xem nội dung đã lưu.');
      }
    } finally {
      if (sent) for (const image of images) URL.revokeObjectURL(image.url);
      setPendingImages([]);
      setPendingText('');
      setReply('');
      setBusy(false);
      locked.current = false;
    }
  }, [active, preview?.version, account, messages, refresh]);

  useEffect(() => {
    const prompt = params.get('q');
    if (!initializing && prompt && !started.current) {
      started.current = true;
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void send(prompt);
    }
  }, [initializing, params, send]);

  const apply = async (edit?: Parameters<typeof examChatApi.edit>[2]) => {
    if (active === null || !preview || locked.current) return;
    locked.current = true;
    setBusy(true);
    setError('');
    try {
      if (edit) {
        setPreview(await examChatApi.edit(active, preview.version, edit));
        setEditing(false);
      } else {
        const result = await examChatApi.confirm(active, preview.version, preview.offer?.count);
        setPreview(result.preview);
        if (result.draft) account?.loadCredits();
        await refresh(active);
      }
    } catch (cause) {
      setError(examChatError(cause));
      await refresh(active).catch(() => {});
    } finally {
      setBusy(false);
      locked.current = false;
    }
  };

  const older = async () => {
    if (active === null || !messages.length || locked.current) return;
    locked.current = true;
    setBusy(true);
    try {
      const page = await examChatApi.transcript(active, messages[0].message_id);
      setMessages((current) => [...page, ...current]);
      setHasOlder(page.length === 80);
    } catch (cause) {
      setError(examChatError(cause));
    } finally {
      locked.current = false;
      setBusy(false);
    }
  };

  return (
    <div className="mx-auto grid min-h-[calc(100dvh-var(--student-header-height))] w-full max-w-7xl gap-4 p-4 lg:grid-cols-[13rem_minmax(0,1fr)_22rem]">
      <aside aria-label="Đoạn chat" className="grid content-start gap-2">
        <Button variant="secondary" onClick={clear} disabled={busy}>Đoạn chat mới</Button>
        <label className="grid gap-1 text-caption lg:sr-only">
          Đoạn chat đã lưu
          <select className={field} value={active ?? ''} disabled={busy} onChange={(e) => e.target.value ? void select(Number(e.target.value)) : clear()}>
            <option value="">Đoạn chat mới</option>
            {sessions.map((item) => <option key={item.session_id} value={item.session_id}>{item.title}</option>)}
          </select>
        </label>
        <ul className="hidden max-h-[65dvh] overflow-auto lg:grid">
          {sessions.map((item) => <li key={item.session_id}><button type="button" title={item.title} aria-current={item.session_id === active}
            className="w-full truncate rounded-lg px-3 py-2 text-left text-label hover:bg-surface aria-current:bg-surface-muted"
            onClick={() => void select(item.session_id)} disabled={busy}>{item.title}</button></li>)}
        </ul>
      </aside>

      <section className="flex min-w-0 flex-col gap-3" aria-label="Trò chuyện với Examind"
        onDragOver={(event) => { if (event.dataTransfer.types.includes('Files')) event.preventDefault(); }}
        onDrop={(event) => {
          if (!event.dataTransfer.files.length) return;
          event.preventDefault();
          if (!busy && !initializing) addImages([...event.dataTransfer.files], attachments, setAttachments, toast, EXAM_CHAT_IMAGES);
        }}>
        <h1 className="text-h3 font-semibold">Tạo đề với AI</h1>
        <div ref={scroll} className="grid max-h-[60dvh] min-h-36 flex-1 content-start gap-3 overflow-auto" aria-live="polite">
          {hasOlder && <Button size="sm" variant="secondary" onClick={() => void older()} disabled={busy}>Xem tin nhắn cũ hơn</Button>}
          {!messages.length && !pendingText && !pendingImages.length && !initializing && <div className="flex flex-wrap gap-2" data-tour="chat-starters">
            {starter.map((text) => <Button key={text} variant="secondary" onClick={() => void send(text)} disabled={busy}>{text}</Button>)}
          </div>}
          {messages.map((item) => <Message key={item.message_id} role={item.role} content={item.content}
            images={active === null ? [] : (item.attachments ?? []).map((image) => ({
              url: chatAttachmentUrl(active, image.attachment_id), label: 'Ảnh ' + image.position,
            }))} />)}
          {(pendingText || pendingImages.length > 0) && <Message role="student" content={pendingText}
            images={pendingImages.map((image) => ({ url: image.url, label: image.file.name }))} />}
          {reply && <Message role="assistant" content={reply} />}
          {busy && !reply && <p className="text-caption text-muted-foreground">Đang xử lý…</p>}
        </div>
        {error && <p role="alert" className="text-label text-danger">{error}</p>}
        {retryText !== null && <Button variant="secondary" onClick={() => void send(retryText, attachments)} disabled={busy}>Gửi lại tin nhắn</Button>}
        {error && retryText === null && active === null && <Button variant="secondary" onClick={() => void initialize()}>Tải lại</Button>}
        <Composer imageLimits={EXAM_CHAT_IMAGES} maxLength={2000} disabled={busy || initializing}
          onSend={(text, images) => void send(text, images)} attachments={attachments} setAttachments={setAttachments} />
      </section>

      <aside aria-label="Bản xem trước" className="min-w-0">
        {preview && <div className="grid gap-3 rounded-2xl border border-border bg-surface p-4">
          <h2 className="text-h4 font-semibold">Cấu trúc đề</h2>
          {preview.operation && <p className="text-label">{preview.operation.kind === 'replace'
            ? 'Đổi câu ' + preview.operation.positions.join(', ') : 'Đổi bộ câu, giữ cấu trúc'}</p>}
          {preview.structure.kind === 'EXAM_TEMPLATE'
            ? <div className="grid gap-2 text-label">
                <p className="font-semibold">{preview.structure.template_name}</p>
                {preview.structure.source && <p>{preview.structure.source}</p>}
                {preview.structure.sections.map((section) => <div key={section.order}>
                  <p>{section.title} · {section.count} câu</p>
                  <p className="text-caption text-muted-foreground">{Object.entries(section.difficulty_distribution ?? {})
                    .map(([level, count]) => difficultyLabels[level as StructureRow['difficulty']] + ' ' + count).join(' · ')}</p>
                </div>)}
                <p className="text-caption">Nhắn tên chương nếu muốn thu hẹp phạm vi.</p>
              </div>
            : editing
              ? <MatrixEditor key={preview.version} preview={preview} catalog={catalog} busy={busy}
                  onCancel={() => setEditing(false)} onSave={(rows, minutes, weights) => void apply({ rows, duration_minutes: minutes, type_point_weights: weights })} />
              : <>
                  <p className="text-label">{preview.structure.chapters.reduce((n, chapter) => n + chapter.count, 0)} câu
                    {preview.structure.duration_minutes ? ' · ' + preview.structure.duration_minutes + ' phút' : ''}</p>
                  <p className="text-caption text-muted-foreground">
                    Trọng số điểm: {TYPES.map((type) => `${typeLabels[type]} ${(preview.structure.kind === 'CHAPTER'
                      ? preview.structure.type_point_weights ?? defaultPointWeights : defaultPointWeights)[type]}`).join(' · ')}
                  </p>
                  <ul className="grid max-h-56 gap-1 overflow-auto text-caption">
                    {(preview.structure.rows ?? []).map((row) => <li key={[row.chapter, row.type, row.difficulty].join('-')}>
                      {catalog[row.chapter] ?? row.chapter} · {typeLabels[row.type]} · {difficultyLabels[row.difficulty]} · {row.count} câu
                    </li>)}
                  </ul>
                  <div className="flex flex-wrap gap-2">
                    <Button size="sm" variant="secondary" disabled={busy} onClick={() => setEditing(true)}>Chỉnh ma trận</Button>
                    <Button size="sm" variant="secondary" disabled={busy} onClick={() => void send("Phân bổ lại ma trận, giữ các ràng buộc hiện tại")}>Phân bổ lại</Button>
                  </div>
                </>}
          {preview.offer && <div className="grid gap-1 text-caption" role="status">
            <p className="font-semibold">Kho đáp ứng {preview.offer.count}/{preview.offer.requested} câu</p>
            {preview.offer.shortages.map((shortage, index) => <p key={index}>
              {shortage.chapter ? catalog[shortage.chapter] ?? shortage.chapter : 'Phần ' + (shortage.section_order ?? 'đề')}
              {shortage.difficulty ? ' · ' + difficultyLabels[shortage.difficulty] : ''} · thiếu {shortage.requested - shortage.available} câu
            </p>)}
          </div>}
          {preview.status !== 'BUILT' && !editing && <Button disabled={busy} onClick={() => void apply()}>
            {preview.offer ? (preview.operation ? 'Chấp nhận đổi một phần' : 'Dùng đề ' + preview.offer.count + ' câu')
              : draft ? 'Xác nhận chỉnh đề' : 'Dựng đề'}
            {' · ' + (draft ? 'Miễn phí' : '100 credit')}
          </Button>}
        </div>}
        {draft && <div className="mt-3 grid gap-2 rounded-2xl border border-border p-4">
          <p className="font-semibold">{draft.title} · {draft.items.length} câu</p>
          <Button href={draftLink(draft) + '/take'}>Làm bài online</Button>
          <Button href={draftLink(draft)} variant="secondary">Xem đề</Button>
          <Button href="/exams" variant="secondary">Đề của tôi</Button>
        </div>}
      </aside>
    </div>
  );
}

function Message({ role, content, images = [] }: {
  role: ServerMessage['role']; content: string; images?: Array<{ url: string; label: string }>;
}) {
  return <div className={'max-w-full whitespace-pre-wrap break-words rounded-2xl p-3 text-body ' +
    (role === 'student' ? 'ml-auto bg-primary-subtle' : 'mr-auto bg-surface')}>
    <span className="sr-only">{role === 'student' ? 'Bạn. ' : 'Examind. '}</span>
    {images.length > 0 && <ul aria-label="Ảnh đính kèm" className="flex flex-wrap justify-end gap-2">
      {images.map((image, index) => <li key={image.url + index}>
        <a href={image.url} target="_blank" rel="noopener noreferrer">
          {/* eslint-disable-next-line @next/next/no-img-element -- ảnh blob hoặc URL riêng có xác thực */}
          <img src={image.url} alt={image.label} className="max-h-40 max-w-44 rounded-lg object-contain" />
        </a>
      </li>)}
    </ul>}
    {content && <p className={images.length ? 'mt-2' : undefined}>{content}</p>}
  </div>;
}

function MatrixEditor({ preview, catalog, busy, onSave, onCancel }: {
  preview: ServerPreview; catalog: Record<string, string>; busy: boolean;
  onSave: (rows: StructureRow[], minutes: number, weights: PointWeights) => void; onCancel: () => void;
}) {
  const structure = preview.structure.kind === 'CHAPTER' ? preview.structure : null;
  const [rows, setRows] = useState(() => (structure?.rows ?? []).map((row, index) => ({ id: index, ...row })));
  const [minutes, setMinutes] = useState(structure?.duration_minutes ?? 0);
  const [weights, setWeights] = useState(structure?.type_point_weights ?? defaultPointWeights);
  const counter = useRef(rows.length);
  const total = rows.reduce((n, row) => n + row.count, 0);
  const change = (id: number, patch: Partial<StructureRow>) => setRows((list) => list.map((row) => row.id === id ? { ...row, ...patch } : row));
  return <form className="grid gap-2" onSubmit={(event) => {
    event.preventDefault();
    onSave(rows.map(({ chapter, type, difficulty, count }) => ({ chapter, type, difficulty, count })), minutes, weights);
  }}>
    {rows.map((row) => <fieldset key={row.id} className="grid grid-cols-2 gap-1 rounded-xl border border-border p-2">
      <select aria-label="Chương" className={field + ' col-span-2'} value={row.chapter} onChange={(e) => change(row.id, { chapter: e.target.value })}>
        {Object.entries(catalog).map(([code, name]) => <option key={code} value={code}>{name}</option>)}
      </select>
      <select aria-label="Dạng câu" className={field} value={row.type} onChange={(e) => change(row.id, { type: e.target.value as StructureRow['type'] })}>
        {TYPES.map((type) => <option key={type} value={type}>{typeLabels[type]}</option>)}
      </select>
      <select aria-label="Độ khó" className={field} value={row.difficulty} onChange={(e) => change(row.id, { difficulty: e.target.value as StructureRow['difficulty'] })}>
        {DIFFICULTIES.map((level) => <option key={level} value={level}>{difficultyLabels[level]}</option>)}
      </select>
      <input aria-label="Số câu" type="number" required min={1} max={50} className={field} value={row.count} onChange={(e) => change(row.id, { count: Number(e.target.value) })} />
      <Button size="sm" type="button" variant="secondary" onClick={() => setRows((list) => list.filter((item) => item.id !== row.id))}>Bỏ hàng</Button>
    </fieldset>)}
    <fieldset className="grid gap-2 rounded-xl border border-border p-2">
      <legend className="px-1 text-caption">Trọng số điểm theo dạng câu</legend>
      {TYPES.map((type) => <label key={type} className="grid grid-cols-[1fr_5rem] items-center gap-2 text-caption">
        {typeLabels[type]}
        <input className={field} type="number" min={1} max={100} required value={weights[type]}
          onChange={(event) => setWeights((current) => ({ ...current, [type]: Number(event.target.value) }))} />
      </label>)}
    </fieldset>
    <p className="text-caption">{total}/50 câu</p>
    <label className="grid gap-1 text-caption">Thời lượng phút (0 là không giới hạn)
      <input type="number" className={field} min={0} max={300} required value={minutes} onChange={(event) => setMinutes(Number(event.target.value))} />
    </label>
    <Button size="sm" type="button" variant="secondary" disabled={rows.length >= 50 || !Object.keys(catalog).length} onClick={() => {
      const id = counter.current++;
      setRows((list) => [...list, { id, chapter: list[0]?.chapter ?? Object.keys(catalog)[0], type: 'SINGLE_CHOICE', difficulty: 'TH', count: 1 }]);
    }}>Thêm hàng</Button>
    <Button size="sm" type="submit" disabled={busy || total < 1 || total > 50}>Áp dụng ma trận</Button>
    <Button size="sm" type="button" variant="secondary" onClick={onCancel}>Hủy chỉnh</Button>
  </form>;
}
