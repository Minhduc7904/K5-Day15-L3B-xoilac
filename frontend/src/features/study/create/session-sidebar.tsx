'use client';

import { Check, FileCheck2, ListTree, MessageCircle, PanelLeftClose, Pencil, Plus, Search, Trash2, X } from 'lucide-react';
import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { cn } from '@/lib/cn';
import { examDuration } from '../format';
import { groupSessions, type ChatSession } from './sessions';

interface Props {
  sessions: ChatSession[];
  activeId: string;
  busyId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onRename: (id: string, title: string) => void;
  onRemove: (id: string) => void;
  onCollapse: () => void;
}

const iconBtn =
  'flex size-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-surface-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring';

/** Danh sách đoạn chat tạo đề: tạo mới, tìm, đổi tên, xoá. */
export function SessionSidebar({ sessions, activeId, busyId, onSelect, onCreate, onRename, onRemove, onCollapse }: Props) {
  const [query, setQuery] = useState('');
  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    const list = sessions.filter((s) => s.persisted || s.id === activeId);
    return q ? list.filter((s) => s.title.toLowerCase().includes(q)) : list;
  }, [sessions, query, activeId]);
  const groups = groupSessions(visible);

  return (
    <nav aria-label="Các đoạn chat" className="flex h-full w-full flex-col bg-surface">
      <div className="flex items-center justify-between gap-2 px-3 pt-3 pb-2">
        <h2 className="px-1 text-label font-bold text-foreground">Đoạn chat</h2>
        <button type="button" onClick={onCollapse} className={iconBtn} aria-label="Thu gọn danh sách đoạn chat" title="Thu gọn">
          <PanelLeftClose className="size-4" aria-hidden="true" />
        </button>
      </div>

      <div className="grid gap-2 px-3 pb-3">
        <button
          type="button"
          onClick={onCreate}
          className="flex h-10 items-center justify-center gap-2 rounded-xl bg-primary text-label font-semibold text-primary-foreground shadow-soft transition-colors hover:bg-primary-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
        >
          <Plus className="size-4" aria-hidden="true" /> Đoạn chat mới
        </button>
        <label className="relative block">
          <span className="sr-only">Tìm đoạn chat</span>
          <Search className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Tìm theo tên…"
            className="h-9 w-full rounded-lg border border-border bg-background pr-2 pl-8 text-label text-foreground outline-none placeholder:text-muted-foreground focus:border-ring focus:ring-2 focus:ring-ring/20"
          />
        </label>
      </div>

      <div className="flex-1 overflow-y-auto px-2 pb-4">
        {groups.length === 0 ? (
          <p className="px-3 py-6 text-center text-caption text-muted-foreground">{query ? 'Không có đoạn chat nào khớp.' : 'Chưa có đoạn chat nào.'}</p>
        ) : (
          groups.map((group) => (
            <section key={group.label} aria-label={group.label} className="mt-2 first:mt-0">
              <h3 className="px-2.5 pt-2 pb-1 text-[0.6875rem] font-semibold text-muted-foreground">{group.label}</h3>
              <ul className="grid gap-0.5">
                {group.items.map((s) => (
                  <SessionItem
                    key={s.id}
                    session={s}
                    active={s.id === activeId}
                    busy={s.id === busyId}
                    onSelect={() => onSelect(s.id)}
                    onRename={(title) => onRename(s.id, title)}
                    onRemove={() => onRemove(s.id)}
                  />
                ))}
              </ul>
            </section>
          ))
        )}
      </div>
    </nav>
  );
}

function SessionItem({ session, active, busy, onSelect, onRename, onRemove }: {
  session: ChatSession;
  active: boolean;
  busy: boolean;
  onSelect: () => void;
  onRename: (title: string) => void;
  onRemove: () => void;
}) {
  const [mode, setMode] = useState<'view' | 'rename' | 'confirm'>('view');
  const [draft, setDraft] = useState(session.title);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (mode === 'rename') inputRef.current?.select();
  }, [mode]);

  const total = session.proposal?.rows.reduce((s, r) => s + r.count, 0) ?? 0;
  const Icon = session.built ? FileCheck2 : session.proposal ? ListTree : MessageCircle;
  const meta = busy
    ? 'Đang trả lời…'
    : session.built
      ? 'Đã dựng đề'
      : session.proposal
        ? `Nháp · ${total} câu · ${examDuration(session.proposal.durationMinutes)}`
        : session.messages.length
          ? `${session.messages.length} tin nhắn`
          : session.persisted
            ? 'Đoạn chat đã lưu'
            : 'Chưa có tin nhắn';

  const save = () => {
    onRename(draft);
    setMode('view');
  };
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') save();
    if (e.key === 'Escape') {
      setDraft(session.title);
      setMode('view');
    }
  };

  if (mode === 'rename') {
    return (
      <li className="flex items-center gap-1 rounded-lg bg-background p-1 ring-2 ring-ring/30">
        <label className="sr-only" htmlFor={`rename-${session.id}`}>Tên đoạn chat</label>
        <input
          id={`rename-${session.id}`}
          ref={inputRef}
          value={draft}
          maxLength={80}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKey}
          className="h-8 min-w-0 flex-1 rounded-md px-2 text-label text-foreground outline-none"
        />
        <button type="button" onClick={save} className={iconBtn} aria-label="Lưu tên">
          <Check className="size-4" aria-hidden="true" />
        </button>
        <button type="button" onClick={() => { setDraft(session.title); setMode('view'); }} className={iconBtn} aria-label="Huỷ đổi tên">
          <X className="size-4" aria-hidden="true" />
        </button>
      </li>
    );
  }

  if (mode === 'confirm') {
    return (
      <li role="alertdialog" aria-label="Xác nhận xoá đoạn chat" className="grid gap-2 rounded-lg border border-danger/30 bg-danger-subtle p-2.5">
        <p className="text-caption text-foreground">
          Xoá <b className="font-semibold">“{session.title}”</b> khỏi danh sách? Không khôi phục được. Đề đã dựng vẫn còn trong “Đề của tôi”.
        </p>
        <div className="flex justify-end gap-1.5">
          <button type="button" autoFocus onClick={() => setMode('view')} className="h-8 rounded-md px-3 text-caption font-semibold text-foreground hover:bg-background focus-visible:outline-2 focus-visible:outline-ring">
            Huỷ
          </button>
          <button type="button" onClick={onRemove} className="h-8 rounded-md bg-danger px-3 text-caption font-semibold text-primary-foreground hover:bg-danger-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring">
            Xoá
          </button>
        </div>
      </li>
    );
  }

  return (
    <li className="group relative">
      <button
        type="button"
        onClick={onSelect}
        aria-current={active ? 'page' : undefined}
        className={cn(
          'grid w-full grid-cols-[auto_minmax(0,1fr)] items-start gap-2.5 rounded-lg px-2.5 py-2 text-left transition-colors focus-visible:outline-2 focus-visible:outline-ring',
          active ? 'bg-background shadow-soft' : 'hover:bg-surface-muted',
        )}
      >
        <Icon
          className={cn('mt-0.5 size-4', session.built ? 'text-success' : session.proposal ? 'text-accent-strong' : 'text-muted-foreground', busy && 'animate-pulse')}
          aria-hidden="true"
        />
        <span className="grid min-w-0 pr-12">
          <span className={cn('truncate text-label', active ? 'font-semibold text-foreground' : 'font-medium text-foreground')}>{session.title}</span>
          <span className="truncate text-caption text-muted-foreground">{meta}</span>
        </span>
      </button>
      {session.persisted && (
        <div className="absolute top-1.5 right-1.5 flex gap-0.5 opacity-0 transition-opacity group-focus-within:opacity-100 group-hover:opacity-100 [@media(hover:none)]:opacity-100">
          <button type="button" onClick={() => { setDraft(session.title); setMode('rename'); }} className={iconBtn} aria-label={`Đổi tên “${session.title}”`} title="Đổi tên">
            <Pencil className="size-3.5" aria-hidden="true" />
          </button>
          <button type="button" onClick={() => setMode('confirm')} disabled={busy} className={cn(iconBtn, 'hover:text-danger disabled:opacity-40')} aria-label={`Xoá “${session.title}”`} title="Xoá">
            <Trash2 className="size-3.5" aria-hidden="true" />
          </button>
        </div>
      )}
    </li>
  );
}
