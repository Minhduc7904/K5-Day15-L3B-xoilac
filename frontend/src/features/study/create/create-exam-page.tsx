'use client';

import { BookMarked, CircleAlert, ClipboardList, Download, FileCheck2, ImageIcon, ImageUp, ListTree, Maximize2, Minimize2, PanelLeftOpen, Play, Target, Wand2, X } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import Image from 'next/image';
import { useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useRef, useState, type DragEvent, type ReactNode } from 'react';
import { MascotAnimation } from '@/components/mascot/mascot-animation';
import { Button } from '@/components/ui/button';
import { useToast } from '@/components/ui/toast';
import { cn } from '@/lib/cn';
import { examChatApi, examChatError, type ServerPreview, type StudentPlan } from '../exam-chat-api';
import { QuestionContent } from '../components/question-content';
import { ExamPaperDialog } from '../exams/exam-paper';
import { examDuration } from '../format';
import { difficultyLabels } from '../labels';
import { useStudentAccount } from '../profile/student-account-provider';
import type { Exam, StructureProposal } from '../types';
import { addImages, Composer, type Attachment } from './composer';
import { MatrixDialog } from './matrix-dialog';
import { allocate, DIFFS, distribute, parentOf, planFromRows, planTotal, TYPES, type ExamPlan } from './plan';
import { SessionSidebar } from './session-sidebar';
import { builtCard, shortageText, toProposal, uid, useChatSessions, type ChatMessage } from './sessions';
import { StructurePreview } from './structure-preview';

const STARTERS = [
  { icon: Target, title: 'Ôn chương mình hay sai', text: 'Tạo đề ôn tiếp', hint: 'Agent xem lịch sử làm bài để chọn chương' },
  { icon: BookMarked, title: 'Theo một chương cụ thể', text: 'Ra đề 20 phút về nguyên hàm và tích phân', hint: 'Vd: tích phân, mũ – lôgarit, Oxyz…' },
  { icon: ClipboardList, title: 'Luyện thoải mái, không tính giờ', text: 'Cho mình đề không giới hạn thời gian về hàm số mũ và lôgarit', hint: 'Làm chậm, hiểu kỹ từng câu' },
  { icon: ImageUp, title: 'Gửi ảnh bài hay sai', text: '', hint: 'Đính kèm ảnh, agent gợi ý chương cần ôn', attach: true },
];

type PanelState = 'open' | 'min';

/** Kế hoạch tổng quan học sinh vừa chỉnh, gửi kèm tin nhắn để agent phân bổ lại thành ma trận. */
function studentPlan(plan: ExamPlan): StudentPlan {
  const counts = distribute(planTotal(plan), DIFFS.map((d) => plan.difficulty[d]));
  return {
    chapter_counts: Object.fromEntries(plan.chapters.filter((c) => c.count > 0).map((c) => [c.code, c.count])),
    type_counts: Object.fromEntries(TYPES.filter((t) => plan.types[t] > 0).map((t) => [t, plan.types[t]])),
    difficulty_counts: Object.fromEntries(DIFFS.map((d, i) => [d, counts[i]])),
  };
}

export function CreateExamPage() {
  const params = useSearchParams();
  const toast = useToast();
  const account = useStudentAccount();
  const { sessions, active, activeId, ready, error, select, create, update, rename, remove, loadState, promote, refreshList, flush } = useChatSessions();
  const [busyId, setBusyId] = useState<string | null>(null);
  const [thinking, setThinking] = useState(false);
  const [attachments, setAttachmentsState] = useState<Attachment[]>([]);
  const [dragging, setDragging] = useState(false);
  const [panel, setPanel] = useState<PanelState>('open');
  const [matrixOpen, setMatrixOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const autoSent = useRef(false);
  const sessionsRef = useRef<{ persisted: (id: string) => boolean }>({ persisted: () => false });
  useEffect(() => {
    sessionsRef.current = { persisted: (id: string) => sessions.find((x) => x.id === id)?.persisted ?? false };
  }, [sessions]);

  useEffect(() => {
    if (error) toast({ tone: 'danger', title: 'Chưa tải được đoạn chat', description: error });
  }, [error, toast]);

  const busy = busyId !== null && busyId === activeId;
  const streaming = busy && !thinking;
  const messages = active?.messages ?? [];
  const proposal = active?.proposal ?? null;
  const draft = active?.draft ?? null;
  const built = active?.built ?? false;
  const preview = active?.preview ?? null;
  const template = preview && preview.status !== 'CANCELLED' && preview.structure.kind === 'EXAM_TEMPLATE' ? preview : null;
  const hasPanel = !!proposal || !!template;
  const free = !!active?.serverDraft;
  const offer = !built && preview?.offer
    ? { count: preview.offer.count, requested: preview.offer.requested, shortages: preview.offer.shortages.map(shortageText) }
    : null;

  const setAttachments = useCallback((updater: (prev: Attachment[]) => Attachment[]) => setAttachmentsState(updater), []);

  // Cuộn xuống tin mới nhất khi có nội dung mới hoặc đổi đoạn chat.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, [messages, thinking, activeId]);

  const send = useCallback(
    async (sessionId: string, text: string, files: Attachment[] = [], plan: ExamPlan | null = null) => {
      const images = files.map((f) => ({ url: f.url, name: f.file.name }));
      setAttachmentsState([]);
      setBusyId(sessionId);
      setThinking(true);
      let sid = sessionId;
      const replyId = uid();
      let started = false;
      let gotPreview = false;
      let sent = false;
      let persisted: boolean = sessionsRef.current.persisted(sid);
      const edit = (fn: (m: ChatMessage) => ChatMessage) =>
        update(sid, (s) => ({ ...s, updatedAt: new Date().toISOString(), messages: s.messages.map((m) => (m.id === replyId ? fn(m) : m)) }));
      const ensureReply = () => {
        if (started) return;
        started = true;
        setThinking(false);
        update(sid, (s) => ({ ...s, messages: [...s.messages, { id: replyId, role: 'assistant', text: '' }] }));
      };
      try {
        // Tin đầu tiên mới tạo phiên trên server; chỉnh sửa chưa lưu trên bảng cấu trúc được gửi trước khi nhắn.
        if (!persisted) {
          sid = await promote(sid);
          persisted = true;
        }
        setBusyId(sid);
        const current = await flush(sid);
        update(sid, (s) => ({
          ...s,
          title: s.messages.length === 0 ? (text.length > 48 ? `${text.slice(0, 46)}…` : text) : s.title,
          updatedAt: new Date().toISOString(),
          messages: [...s.messages, { id: uid(), role: 'student', text, images }],
        }));
        const version = current && current.status !== 'CANCELLED' ? current.version : 0;
        for await (const ev of examChatApi.send(Number(sid), text, version, files.map((f) => f.file), plan ? studentPlan(plan) : undefined)) {
          if (ev.event === 'error') throw new Error(ev.data.message);
          if (ev.event === 'message') {
            ensureReply();
            edit((m) => ({ ...m, text: m.text + ev.data.delta }));
          } else if (ev.event === 'preview' && ev.data) {
            gotPreview = true;
            ensureReply();
            const next = ev.data;
            update(sid, (s) => ({ ...s, preview: next, proposal: toProposal(next), built: next.status === 'BUILT', draft: null, dirty: false }));
            edit((m) => ({ ...m, proposal: true }));
            setPanel('open');
          } else if (ev.event === 'draft') {
            ensureReply();
            account?.loadCredits();
            update(sid, (s) => ({ ...s, built: true }));
            edit((m) => ({ ...m, built: builtCard(ev.data) }));
          } else if (ev.event === 'done') {
            sent = true;
          }
        }
        // Đồng bộ lại với server: mã tin nhắn, ảnh đã lưu, thẻ đề và tên đoạn chat do server đặt.
        await loadState(sid, !gotPreview);
        await refreshList().catch(() => {});
        for (const f of files) URL.revokeObjectURL(f.url);
      } catch (cause) {
        if (persisted) await loadState(sid, true).catch(() => {});
        const known = sent ? 'Tin nhắn đã gửi nhưng mình chưa nhận đủ phản hồi. Bạn tải lại đoạn chat để xem nhé.' : examChatError(cause);
        update(sid, (s) => ({ ...s, messages: [...s.messages, { id: uid(), role: 'assistant', text: known || 'Mình bị mất kết nối giữa chừng. Bạn gửi lại tin nhắn nhé.' }] }));
      } finally {
        setThinking(false);
        setBusyId(null);
      }
    },
    [update, promote, flush, loadState, refreshList, account],
  );

  // Đến từ lối tắt trên dashboard: gửi luôn câu đã nhập vào một đoạn chat mới.
  useEffect(() => {
    const q = params.get('q');
    if (q && ready && activeId && !autoSent.current) {
      autoSent.current = true;
      // Bỏ ?q khỏi URL để tải lại trang không gửi lại câu đó vào đoạn chat mới.
      window.history.replaceState(null, '', '/exams/new');
      void send(activeId, q);
    }
  }, [params, ready, activeId, send]);

  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (busy) return;
    addImages([...e.dataTransfer.files], attachments, setAttachments, toast);
  };

  const switchTo = (id: string) => {
    attachments.forEach((a) => URL.revokeObjectURL(a.url));
    setAttachmentsState([]);
    setMatrixOpen(false);
    setPanel('open');
    select(id);
    setDrawerOpen(false);
  };
  const startNew = () => switchTo(create());

  const setProposal = (next: StructureProposal) => update(activeId, (s) => ({ ...s, proposal: next, dirty: true }));
  const fail = (cause: unknown) => toast({ tone: 'danger', title: 'Chưa thực hiện được', description: examChatError(cause) });

  /** Dựng đề từ bản xem trước hiện tại. Kho thiếu câu thì server trả đề xuất rút gọn để học sinh đồng ý. */
  const build = async () => {
    if (!active?.persisted || busyId) return;
    setBusyId(activeId);
    try {
      const current = await flush(activeId);
      if (!current) return;
      const result = await examChatApi.confirm(Number(activeId), current.version, current.offer?.count);
      if (result.draft) account?.loadCredits();
      await loadState(activeId, !result.draft);
      await refreshList().catch(() => {});
      if (!result.draft && result.message) toast({ tone: 'warning', title: 'Cần bạn xác nhận', description: result.message });
    } catch (cause) {
      fail(cause);
      await loadState(activeId, true).catch(() => {});
    } finally {
      setBusyId(null);
    }
  };
  const setDraft = (plan: ExamPlan) => {
    // Chỉnh về đúng như ma trận hiện tại thì coi như chưa chỉnh.
    const base = proposal ? planFromRows(proposal.rows) : null;
    const same = base && JSON.stringify(base) === JSON.stringify(plan);
    update(activeId, (s) => ({ ...s, draft: same ? null : plan }));
  };

  const total = draft ? planTotal(draft) : (proposal?.rows.reduce((s, r) => s + r.count, 0) ?? 0);
  const matrixRows = draft ? allocate(draft) : (proposal?.rows ?? []);
  const matrixParents = draft ? draft.chapters.map((c) => c.code) : [...new Set(matrixRows.map((r) => parentOf(r.chapter)))];

  const sidebar = (
    <SessionSidebar
      sessions={sessions}
      activeId={activeId}
      busyId={busyId}
      onSelect={switchTo}
      onCreate={startNew}
      onRename={(id, title) => void rename(id, title).catch(fail)}
      onRemove={(id) => void remove(id).catch(fail)}
      onCollapse={() => (drawerOpen ? setDrawerOpen(false) : setSidebarCollapsed(true))}
    />
  );

  if (!ready) return <div className="h-[calc(100dvh-var(--student-header-height))] min-h-80 bg-background" aria-busy="true" />;

  return (
    <div className="flex h-[calc(100dvh-var(--student-header-height))] min-h-80 bg-background">
      {/* Danh sách đoạn chat: cột trái trên màn hình rộng */}
      {!sidebarCollapsed && <aside className="hidden w-72 shrink-0 border-r border-border lg:block">{sidebar}</aside>}

      {/* Ngăn kéo cho điện thoại / máy tính bảng */}
      <AnimatePresence>
        {drawerOpen && (
          <div className="fixed inset-0 z-40 lg:hidden">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0 bg-foreground/40" onClick={() => setDrawerOpen(false)} />
            <motion.aside
              initial={{ x: '-100%' }}
              animate={{ x: 0 }}
              exit={{ x: '-100%' }}
              transition={{ type: 'spring', stiffness: 360, damping: 36 }}
              className="absolute inset-y-0 left-0 w-[min(20rem,86vw)] shadow-lift"
            >
              {sidebar}
            </motion.aside>
          </div>
        )}
      </AnimatePresence>

      {/* Khung chat */}
      <section
        aria-label="Trò chuyện với Examind"
        className="relative flex min-w-0 flex-1 flex-col"
        onDragEnter={(e) => {
          if (e.dataTransfer.types.includes('Files')) setDragging(true);
        }}
        onDragOver={(e) => e.preventDefault()}
        onDragLeave={(e) => {
          if (!e.currentTarget.contains(e.relatedTarget as Node)) setDragging(false);
        }}
        onDrop={onDrop}
      >
        <header className="flex h-14 shrink-0 items-center gap-2 border-b border-border px-3 sm:px-4">
          <button type="button" onClick={() => setDrawerOpen(true)} className={headerBtn + ' lg:hidden'} aria-label="Mở danh sách đoạn chat">
            <PanelLeftOpen className="size-5" aria-hidden="true" />
          </button>
          {sidebarCollapsed && (
            <button type="button" onClick={() => setSidebarCollapsed(false)} className={headerBtn + ' hidden lg:flex'} aria-label="Mở danh sách đoạn chat" title="Mở danh sách">
              <PanelLeftOpen className="size-5" aria-hidden="true" />
            </button>
          )}
          <div className="grid min-w-0 flex-1">
            <h1 className="truncate text-label font-bold text-foreground">{active?.messages.length ? active.title : 'Tạo đề với AI'}</h1>
            <p className="flex items-center gap-1.5 text-caption text-muted-foreground" aria-live="polite">
              <span className={cn('size-2 rounded-full', busy ? 'animate-pulse bg-warning' : 'bg-success')} aria-hidden="true" />
              {busy ? (thinking ? 'Đang suy nghĩ…' : 'Đang trả lời…') : 'Examind sẵn sàng'}
            </p>
          </div>
        </header>

        {/* Vùng tin nhắn, bảng cấu trúc nổi phía trên */}
        <div className="relative min-h-0 flex-1">
          <div
            ref={scrollRef}
            className={cn('h-full overflow-y-auto px-4 py-6 transition-[padding] duration-300 sm:px-6', hasPanel && panel === 'open' && 'xl:pr-[25rem]')}
            aria-live="polite"
            aria-busy={busy}
          >
            <div className="mx-auto grid max-w-3xl gap-5">
              {messages.length === 0 ? (
                <Welcome
                  onPick={(s) => {
                    if (s.attach) document.querySelector<HTMLButtonElement>('button[aria-label^="Đính kèm ảnh"]')?.click();
                    else void send(activeId, s.text);
                  }}
                />
              ) : (
                messages.map((m) => (
                  <Bubble key={m.id} message={m} streaming={streaming && m === messages.at(-1)} onOpenPreview={() => setPanel('open')} />
                ))
              )}
              <AnimatePresence>{busy && thinking && <Thinking />}</AnimatePresence>
            </div>
          </div>

          <AnimatePresence mode="wait">
            {proposal && panel === 'min' && (
              <motion.button
                key="pill"
                type="button"
                onClick={() => setPanel('open')}
                initial={{ opacity: 0, scale: 0.9, y: -6 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9 }}
                className="absolute top-3 right-3 z-20 flex items-center gap-2 rounded-full border border-border bg-background py-1.5 pr-2 pl-3 text-caption font-semibold text-foreground shadow-lift hover:border-primary/40 focus-visible:outline-2 focus-visible:outline-ring"
              >
                <ListTree className="size-4 text-accent-strong" aria-hidden="true" />
                Cấu trúc đề · {total} câu · {examDuration(proposal.durationMinutes)}
                {draft && <span className="size-2 rounded-full bg-warning" aria-label="Có thay đổi chưa phân bổ" />}
                <Maximize2 className="size-3.5 text-muted-foreground" aria-hidden="true" />
              </motion.button>
            )}
            {proposal && panel === 'open' && (
              <FloatingPanel key="panel" title={proposal.title} built={built} onTitle={(title) => setProposal({ ...proposal, title })} onMinimize={() => setPanel('min')}>
                <StructurePreview
                  proposal={proposal}
                  draft={draft}
                  busy={busy}
                  built={built}
                  onProposalChange={setProposal}
                  onDraftChange={setDraft}
                  onCreate={() => void build()}
                  onAcceptOffer={() => void build()}
                  onRebalance={() => draft && void send(activeId, 'Phân bổ lại ma trận theo tổng quan mình vừa chỉnh', [], draft)}
                  onAdvanced={() => setMatrixOpen(true)}
                  free={free}
                  offer={offer}
                />
              </FloatingPanel>
            )}
            {template && panel === 'open' && (
              <FloatingPanel key="template" title={template.structure.kind === 'EXAM_TEMPLATE' ? template.structure.template_name : ''} built={built} readOnly onTitle={() => {}} onMinimize={() => setPanel('min')}>
                <TemplateSummary preview={template} busy={busy} free={free} offer={offer} onBuild={() => void build()} />
              </FloatingPanel>
            )}
          </AnimatePresence>
        </div>

        <div className={cn('shrink-0 px-3 pt-2 pb-[max(0.75rem,env(safe-area-inset-bottom))] transition-[padding] duration-300 sm:px-6', hasPanel && panel === 'open' && 'xl:pr-[25rem]')}>
          <div className="mx-auto max-w-3xl">
            <Composer
              disabled={busy}
              onSend={(t, a) => void send(activeId, t || 'Mình gửi ảnh bài mình hay sai', a)}
              attachments={attachments}
              setAttachments={setAttachments}
              placeholder={proposal && !built ? 'Chỉnh bằng lời: "thêm 2 câu", "khó hơn", "45 phút"… hoặc gõ "xác nhận"' : undefined}
            />
          </div>
        </div>

        <AnimatePresence>
          {dragging && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="pointer-events-none absolute inset-3 z-30 grid place-items-center rounded-3xl border-2 border-dashed border-primary bg-primary-subtle/90"
            >
              <div className="grid justify-items-center gap-2 text-primary">
                <ImageUp className="size-10" aria-hidden="true" />
                <p className="text-h3">Thả ảnh vào đây</p>
                <p className="text-caption">Tối đa 4 ảnh, mỗi ảnh 5 MB</p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </section>

      <AnimatePresence>
        {matrixOpen && proposal && (
          <MatrixDialog
            rows={matrixRows}
            parents={matrixParents}
            onClose={() => setMatrixOpen(false)}
            onApply={(rows) => {
              setMatrixOpen(false);
              const next = { ...proposal, rows };
              update(activeId, (s) => (s.proposal ? { ...s, proposal: next, draft: null, dirty: true } : s));
              flush(activeId, next).then(
                () => toast({ tone: 'success', title: 'Đã áp dụng ma trận', description: `${rows.reduce((s, r) => s + r.count, 0)} câu. Bấm "Tạo đề" khi bạn ưng.` }),
                async (cause) => {
                  fail(cause);
                  await loadState(activeId).catch(() => {});
                },
              );
            }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

const headerBtn =
  'flex size-9 shrink-0 items-center justify-center rounded-lg text-muted-foreground transition-colors hover:bg-surface hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring';

/**
 * Bảng cấu trúc đề nổi trên khung chat: góc phải trên màn hình rộng, ngăn kéo từ dưới lên trên điện thoại.
 * Thu nhỏ thành viên thuốc ở góc phải để nhường chỗ cho cuộc trò chuyện.
 */
function FloatingPanel({ title, built, readOnly, onTitle, onMinimize, children }: { title: string; built: boolean; readOnly?: boolean; onTitle: (t: string) => void; onMinimize: () => void; children: ReactNode }) {
  return (
    <>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-30 bg-foreground/35 lg:hidden"
        onClick={onMinimize}
        aria-hidden="true"
      />
      <motion.aside
        aria-label="Cấu trúc đề"
        initial={{ opacity: 0, y: 24, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 16, scale: 0.98 }}
        transition={{ type: 'spring', stiffness: 380, damping: 34 }}
        style={{ originX: 1, originY: 0 }}
        className="fixed inset-x-0 bottom-0 z-40 flex max-h-[86dvh] flex-col overflow-hidden rounded-t-2xl border border-border bg-background shadow-lift lg:absolute lg:inset-x-auto lg:top-3 lg:right-3 lg:bottom-3 lg:z-20 lg:max-h-none lg:w-[22.5rem] lg:rounded-2xl"
      >
        <span className="mx-auto mt-2 h-1.5 w-10 rounded-full bg-border lg:hidden" aria-hidden="true" />
        <div className="flex items-center gap-2 px-4 pt-3 pb-2">
          <span className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-accent-subtle text-accent-strong">
            <ListTree className="size-4" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <label htmlFor="exam-title" className="block text-[0.6875rem] font-medium text-muted-foreground">
              {built ? 'Đề đã dựng' : readOnly ? 'Mẫu kỳ thi · bản nháp' : 'Cấu trúc đề · bản nháp'}
            </label>
            <input
              id="exam-title"
              value={title}
              onChange={(e) => onTitle(e.target.value)}
              disabled={built || readOnly}
              maxLength={120}
              className="-ml-1 w-full truncate rounded-md px-1 text-label font-bold text-foreground outline-none hover:bg-surface focus-visible:bg-surface focus-visible:ring-2 focus-visible:ring-ring/30 disabled:hover:bg-transparent"
            />
          </div>
          <button type="button" onClick={onMinimize} className={headerBtn} aria-label="Thu nhỏ bảng cấu trúc" title="Thu nhỏ">
            <Minimize2 className="size-4 max-lg:hidden" aria-hidden="true" />
            <X className="size-5 lg:hidden" aria-hidden="true" />
          </button>
        </div>
        {children}
      </motion.aside>
    </>
  );
}

function Welcome({ onPick }: { onPick: (s: (typeof STARTERS)[number]) => void }) {
  return (
    <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} className="grid justify-items-center gap-5 py-4 text-center">
      <motion.div animate={{ y: [0, -8, 0] }} transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}>
        <Image src="/brand/mascot/static/welcome.webp" alt="" width={384} height={384} className="pixelated h-auto w-28 drop-shadow-mascot sm:w-36" priority unoptimized />
      </motion.div>
      <div className="grid gap-1.5">
        <h2 className="text-h2 text-balance text-foreground">Hôm nay bạn muốn ôn gì?</h2>
        <p className="mx-auto max-w-lg text-body text-muted-foreground">
          Mình chọn câu đã duyệt trong ngân hàng để ghép đề. Bạn xem trước, chỉnh số câu, dạng câu và độ khó rồi mới tạo đề.
        </p>
      </div>
      <ul data-tour="chat-starters" className="grid w-full gap-2.5 text-left sm:grid-cols-2">
        {STARTERS.map((s, i) => (
          <motion.li key={s.title} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12 + i * 0.06 }}>
            <button
              type="button"
              onClick={() => onPick(s)}
              className="group flex h-full w-full items-start gap-3 rounded-2xl border border-border bg-background p-3.5 text-left transition-[translate,border-color,box-shadow] hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-soft focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
            >
              <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary-subtle text-primary transition-colors group-hover:bg-primary group-hover:text-primary-foreground">
                <s.icon className="size-4.5" aria-hidden="true" />
              </span>
              <span className="grid gap-0.5">
                <span className="text-label font-semibold text-foreground">{s.title}</span>
                <span className="text-caption text-muted-foreground">{s.hint}</span>
              </span>
            </button>
          </motion.li>
        ))}
      </ul>
    </motion.div>
  );
}

function Thinking() {
  return (
    <motion.div initial={{ opacity: 0, y: 10, scale: 0.96 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, scale: 0.96 }} role="status" className="flex items-end gap-3">
      <span className="shrink-0 overflow-hidden rounded-2xl bg-primary-subtle p-1">
        <MascotAnimation motion="thinking" size={56} />
      </span>
      <div className="rounded-2xl rounded-bl-md border border-border bg-background px-4 py-3 shadow-soft">
        <p className="text-caption font-semibold text-muted-foreground">Examind đang suy nghĩ</p>
        <div className="mt-1.5 flex gap-1.5" aria-hidden="true">
          {[0, 1, 2].map((i) => (
            <motion.span key={i} className="size-2 rounded-full bg-primary" animate={{ y: [0, -5, 0], opacity: [0.4, 1, 0.4] }} transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.15 }} />
          ))}
        </div>
      </div>
    </motion.div>
  );
}

function Bubble({ message, streaming, onOpenPreview }: { message: ChatMessage; streaming: boolean; onOpenPreview: () => void }) {
  const mine = message.role === 'student';
  return (
    <motion.article
      initial={{ opacity: 0, y: 12, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ type: 'spring', stiffness: 380, damping: 30 }}
      className={cn('flex gap-3', mine ? 'justify-end' : 'items-start')}
      aria-label={mine ? 'Bạn' : 'Examind'}
    >
      {!mine && (
        <span className="mt-1 hidden size-9 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-primary-subtle sm:flex">
          <Image src="/brand/mascot/static/front.webp" alt="" width={384} height={384} className="pixelated h-auto w-8" unoptimized />
        </span>
      )}
      <div className={cn('grid max-w-[min(36rem,88%)] gap-2', mine && 'justify-items-end')}>
        {message.images && message.images.length > 0 && (
          <ul className={cn('grid gap-1.5', message.images.length > 1 ? 'grid-cols-2' : 'grid-cols-1')}>
            {message.images.map((img, i) => (
              <li key={`${img.name}-${i}`}>
                {img.url ? (
                  // eslint-disable-next-line @next/next/no-img-element -- ảnh người dùng vừa gửi (blob URL)
                  <img src={img.url} alt={img.name} className="max-h-48 w-full rounded-2xl border border-border object-cover" />
                ) : (
                  <span className="flex items-center gap-1.5 rounded-xl bg-surface px-3 py-2 text-caption text-muted-foreground">
                    <ImageIcon className="size-4" aria-hidden="true" /> {img.name}
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
        {(message.text || streaming) && (
          <div className={cn('rounded-2xl px-4 py-2.5', mine ? 'rounded-br-md bg-primary text-primary-foreground' : 'rounded-bl-md border border-border bg-background text-foreground')}>
            {mine ? (
              <p className="text-body whitespace-pre-wrap">{message.text}</p>
            ) : (
              <div className="text-body">
                <QuestionContent source={message.text} className="text-body" />
                {streaming && <span className="ml-0.5 inline-block h-4 w-1.5 animate-pulse rounded-full bg-primary align-middle" aria-hidden="true" />}
              </div>
            )}
          </div>
        )}
        {message.proposal && !message.built && (
          <motion.button
            type="button"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            onClick={onOpenPreview}
            className="flex w-fit items-center gap-2 rounded-xl border border-accent/30 bg-accent-subtle px-3 py-1.5 text-caption font-semibold text-accent-strong hover:border-accent focus-visible:outline-2 focus-visible:outline-ring"
          >
            <ListTree className="size-4" aria-hidden="true" /> Đã cập nhật cấu trúc đề · Mở bảng
          </motion.button>
        )}
        {message.built && <BuiltCard {...message.built} />}
      </div>
    </motion.article>
  );
}

function BuiltCard({ exam, shortages }: { exam: Exam; shortages: string[] }) {
  const [paper, setPaper] = useState(false);
  const count = exam.sections.reduce((s, sec) => s + sec.questionIds.length, 0);
  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.94, y: 10 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 260, damping: 22, delay: 0.1 }}
      className="relative overflow-hidden rounded-2xl border border-success/25 bg-success-subtle p-4"
    >
      <Image src="/brand/mascot/static/success.webp" alt="" width={384} height={384} unoptimized className="pixelated pointer-events-none absolute -right-2 -bottom-2 h-auto w-22" />
      <div className="relative grid gap-3 pr-16">
        <p className="flex items-center gap-2 text-caption font-semibold text-success">
          <FileCheck2 className="size-4" aria-hidden="true" /> Đề nháp đã sẵn sàng
        </p>
        <div>
          <p className="text-h3 text-foreground">{exam.title}</p>
          <p className="text-caption text-muted-foreground">
            {count} câu · {examDuration(exam.durationMinutes)} · {exam.sections.length} phần
          </p>
        </div>
        {shortages.length > 0 && (
          <p className="flex gap-2 rounded-xl bg-background/70 p-2.5 text-caption text-foreground">
            <CircleAlert className="mt-0.5 size-4 shrink-0 text-warning" aria-hidden="true" />
            <span>Ngân hàng thiếu câu: {shortages.join('; ')}.</span>
          </p>
        )}
        <div className="flex flex-wrap gap-2">
          <Button size="sm" href={`/exams/${exam.id}/take`} leftIcon={<Play aria-hidden="true" />}>Làm ngay</Button>
          <Button size="sm" variant="outline" href={`/exams/${exam.id}`}>Xem đề</Button>
          <button
            type="button"
            onClick={() => setPaper(true)}
            aria-label={`Tải đề “${exam.title}” dạng PDF`}
            title="Tải đề (A4, PDF)"
            className="flex size-9 items-center justify-center rounded-xl border border-border bg-background text-foreground transition-colors hover:border-primary/50 hover:text-primary focus-visible:outline-2 focus-visible:outline-ring"
          >
            <Download className="size-4" aria-hidden="true" />
          </button>
        </div>
      </div>
      <AnimatePresence>{paper && <ExamPaperDialog examId={exam.id} onClose={() => setPaper(false)} />}</AnimatePresence>
    </motion.div>
  );
}

/** Mẫu kỳ thi cố định số câu và độ khó từng phần, nên chỉ xem và dựng; muốn thu hẹp chương thì nhắn cho agent. */
function TemplateSummary({ preview, busy, free, offer, onBuild }: {
  preview: ServerPreview; busy: boolean; free: boolean; offer: { count: number; requested: number; shortages: string[] } | null; onBuild: () => void;
}) {
  if (preview.structure.kind !== 'EXAM_TEMPLATE') return null;
  const { sections, source, duration_minutes: minutes } = preview.structure;
  const total = sections.reduce((n, section) => n + section.count, 0);
  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto px-4 pt-1 pb-4">
        <p className="text-label font-semibold text-foreground">
          {total} câu{minutes ? ` · ${examDuration(minutes)}` : ''}
        </p>
        {source && <p className="text-caption text-muted-foreground">{source}</p>}
        <ul className="divide-y divide-border rounded-xl border border-border">
          {sections.map((section) => (
            <li key={section.order} className="grid gap-0.5 px-3 py-2">
              <span className="text-label font-medium text-foreground">{section.title} · {section.count} câu</span>
              <span className="text-caption text-muted-foreground">
                {Object.entries(section.difficulty_distribution ?? {}).map(([level, count]) => `${difficultyLabels[level as keyof typeof difficultyLabels]} ${count}`).join(' · ')}
              </span>
            </li>
          ))}
        </ul>
        <p className="text-caption text-muted-foreground">Nhắn tên chương nếu muốn thu hẹp phạm vi.</p>
        {offer && (
          <div role="status" className="grid gap-0.5 rounded-xl bg-warning-subtle p-2.5 text-caption text-foreground">
            <p className="font-semibold">Ngân hàng chỉ đáp ứng {offer.count}/{offer.requested} câu</p>
            {offer.shortages.map((line) => <p key={line} className="text-muted-foreground">{line}</p>)}
          </div>
        )}
      </div>
      {preview.status !== 'BUILT' && (
        <div className="grid gap-2 border-t border-border bg-background px-4 pt-3 pb-4">
          <Button leftIcon={<Wand2 aria-hidden="true" />} onClick={onBuild} loading={busy}>
            {busy ? 'Đang tạo…' : `${offer ? `Dùng đề ${offer.count} câu` : `Tạo đề ${total} câu`} · ${free ? 'Miễn phí' : '100 credit'}`}
          </Button>
          {!free && <p className="text-[0.6875rem] text-muted-foreground">Lần dựng đầu của mỗi đoạn chat tốn 100 credit; chỉnh lại đề nháp sau đó miễn phí.</p>}
        </div>
      )}
    </div>
  );
}
