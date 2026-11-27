'use client';

import { RotateCcw, Table2, X } from 'lucide-react';
import { motion } from 'motion/react';
import { Fragment, useEffect, useMemo, useRef, useState, type KeyboardEvent } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/cn';
import { chapterOf, typeLabels } from '../fixtures/chapters';
import type { Difficulty, QuestionType, StructureRow } from '../types';
import { DIFFS, MAX_QUESTIONS, parentOf, subchaptersOf, TYPES } from './plan';
import { diffColor, typeColor } from './structure-preview';

const PART = ['Phần I', 'Phần II', 'Phần III'];
const key = (chapter: string, type: QuestionType, diff: Difficulty) => `${chapter}|${type}|${diff}`;

interface Props {
  rows: StructureRow[];
  /** Chương cha đang có trong đề, theo thứ tự hiển thị. */
  parents: string[];
  onApply: (rows: StructureRow[]) => void;
  onClose: () => void;
}

/** Ma trận đề: mỗi dòng một chương con, mỗi cột một dạng câu × mức độ. Học sinh gõ số câu vào từng ô. */
export function MatrixDialog({ rows, parents, onApply, onClose }: Props) {
  const initial = useMemo(() => {
    const map = new Map<string, number>();
    for (const r of rows) map.set(key(r.chapter, r.type, r.difficulty), (map.get(key(r.chapter, r.type, r.difficulty)) ?? 0) + r.count);
    return map;
  }, [rows]);
  const [cells, setCells] = useState(initial);
  const [hideEmpty, setHideEmpty] = useState(false);
  const dialogRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const prev = document.activeElement as HTMLElement | null;
    dialogRef.current?.focus();
    const onKey = (e: globalThis.KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      prev?.focus();
    };
  }, [onClose]);

  const get = (k: string) => cells.get(k) ?? 0;
  const total = [...cells.values()].reduce((s, n) => s + n, 0);
  const over = total > MAX_QUESTIONS;
  const columns = TYPES.flatMap((t) => DIFFS.map((d) => ({ t, d })));
  const colSum = (t: QuestionType, d: Difficulty) => [...cells].filter(([k]) => k.endsWith(`|${t}|${d}`)).reduce((s, [, n]) => s + n, 0);
  const rowSum = (chapter: string) => [...cells].filter(([k]) => k.startsWith(`${chapter}|`)).reduce((s, [, n]) => s + n, 0);
  const parentSum = (parent: string) => [...cells].filter(([k]) => parentOf(k.split('|')[0]) === parent).reduce((s, [, n]) => s + n, 0);

  const set = (k: string, n: number) =>
    setCells((prev) => {
      const next = new Map(prev);
      const v = Math.max(0, Math.min(MAX_QUESTIONS, Number.isFinite(n) ? Math.floor(n) : 0));
      if (v) next.set(k, v);
      else next.delete(k);
      return next;
    });

  const apply = () => {
    const out: StructureRow[] = [];
    for (const [k, count] of cells) {
      const [chapter, type, difficulty] = k.split('|') as [string, QuestionType, Difficulty];
      if (count > 0) out.push({ chapter, type, difficulty, count });
    }
    onApply(out);
  };

  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-2 sm:p-6">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="absolute inset-0 bg-foreground/45 backdrop-blur-[2px]" onClick={onClose} />
      <motion.div
        ref={dialogRef}
        tabIndex={-1}
        role="dialog"
        aria-modal="true"
        aria-labelledby="matrix-title"
        initial={{ opacity: 0, y: 24, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 16, scale: 0.98 }}
        transition={{ type: 'spring', stiffness: 360, damping: 32 }}
        className="relative flex max-h-[92dvh] w-full max-w-6xl flex-col overflow-hidden rounded-2xl bg-background shadow-lift outline-none"
      >
        <header className="flex items-start gap-3 border-b border-border px-4 py-3 sm:px-5">
          <span className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-primary-subtle text-primary">
            <Table2 className="size-5" aria-hidden="true" />
          </span>
          <div className="min-w-0 flex-1">
            <h2 id="matrix-title" className="text-h3 text-foreground">Ma trận đề</h2>
            <p className="text-caption text-muted-foreground">Gõ số câu cho từng chương con theo dạng và mức độ. Phím ↑ ↓ để tăng giảm nhanh.</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Đóng ma trận"
            className="flex size-9 items-center justify-center rounded-lg text-muted-foreground hover:bg-surface-muted hover:text-foreground focus-visible:outline-2 focus-visible:outline-ring"
          >
            <X className="size-5" aria-hidden="true" />
          </button>
        </header>

        <div className="min-h-0 flex-1 overflow-auto">
          <table className="w-full min-w-[56rem] border-separate border-spacing-0 text-label">
            <thead className="sticky top-0 z-20 bg-surface">
              <tr>
                <th rowSpan={2} scope="col" className="sticky left-0 z-10 w-72 border-r border-b border-border bg-surface px-3 py-2 text-left text-caption font-semibold text-foreground">
                  Nội dung
                </th>
                {TYPES.map((t, i) => (
                  <th key={t} colSpan={4} scope="colgroup" className="border-r border-border px-2 pt-2 pb-1 text-center text-caption font-semibold text-foreground">
                    <span className="inline-flex items-center gap-1.5">
                      <i className={cn('size-2.5 rounded-full', typeColor[t])} aria-hidden="true" />
                      {PART[i]} · {typeLabels[t]}
                    </span>
                  </th>
                ))}
                <th rowSpan={2} scope="col" className="w-16 border-b border-border px-2 text-center text-caption font-semibold text-foreground">Tổng</th>
              </tr>
              <tr>
                {columns.map(({ t, d }, i) => (
                  <th
                    key={`${t}-${d}`}
                    scope="col"
                    className={cn('border-b border-border px-1 pb-1.5 text-center text-[0.6875rem] font-semibold text-muted-foreground', i % 4 === 3 && 'border-r')}
                  >
                    <span className="inline-flex items-center gap-1">
                      <i className={cn('size-1.5 rounded-full', diffColor[d])} aria-hidden="true" />
                      {d}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {parents.map((parent) => {
                const subs = subchaptersOf(parent).filter((s) => !hideEmpty || rowSum(s.code) > 0);
                return (
                  <Fragment key={parent}>
                    <tr className="bg-primary-subtle/60">
                      <th scope="rowgroup" colSpan={13} className="sticky left-0 px-3 py-1.5 text-left text-caption font-bold text-primary">
                        {chapterOf(parent).name} <span className="font-medium text-muted-foreground">· Lớp {chapterOf(parent).grade}</span>
                      </th>
                      <td className="px-2 text-center text-caption font-bold text-primary tabular-nums">{parentSum(parent)}</td>
                    </tr>
                    {subs.map((sub) => (
                      <tr key={sub.code} className="group">
                        <th scope="row" className="sticky left-0 z-10 border-r border-b border-border bg-background px-3 py-1 text-left text-caption font-medium text-foreground group-hover:bg-surface">
                          <span className="line-clamp-2">{sub.name}</span>
                        </th>
                        {columns.map(({ t, d }, i) => {
                          const k = key(sub.code, t, d);
                          return (
                            <td key={k} className={cn('border-b border-border p-0.5 text-center group-hover:bg-surface', i % 4 === 3 && 'border-r')}>
                              <Cell
                                value={get(k)}
                                label={`${sub.name}, ${typeLabels[t]}, ${d}`}
                                onChange={(n) => set(k, n)}
                              />
                            </td>
                          );
                        })}
                        <td className="border-b border-border px-2 text-center text-caption font-semibold text-foreground tabular-nums group-hover:bg-surface">{rowSum(sub.code) || ''}</td>
                      </tr>
                    ))}
                  </Fragment>
                );
              })}
            </tbody>
            <tfoot className="sticky bottom-0 z-20 bg-surface">
              <tr>
                <th scope="row" className="sticky left-0 z-10 border-t border-r border-border bg-surface px-3 py-1.5 text-left text-caption font-semibold text-foreground">Tổng số câu</th>
                {columns.map(({ t, d }, i) => (
                  <td key={`${t}-${d}`} className={cn('border-t border-border text-center text-caption font-bold text-foreground tabular-nums', i % 4 === 3 && 'border-r')}>
                    {colSum(t, d)}
                  </td>
                ))}
                <td rowSpan={2} className={cn('border-t border-border text-center text-body font-bold tabular-nums', over ? 'text-danger' : 'text-foreground')}>
                  {total}
                  <span className="block text-[0.6875rem] font-medium text-muted-foreground">/ {MAX_QUESTIONS}</span>
                </td>
              </tr>
              <tr>
                <th scope="row" className="sticky left-0 z-10 border-r border-border bg-surface px-3 py-1.5 text-left text-caption font-semibold text-foreground">Theo phần</th>
                {TYPES.map((t) => (
                  <td key={t} colSpan={4} className="border-r border-border py-1.5 text-center text-caption font-bold text-foreground tabular-nums">
                    {DIFFS.reduce((s, d) => s + colSum(t, d), 0)} câu
                  </td>
                ))}
              </tr>
            </tfoot>
          </table>
        </div>

        <footer className="flex flex-wrap items-center gap-2 border-t border-border px-4 py-3 sm:px-5">
          <label className="mr-auto inline-flex cursor-pointer items-center gap-2 text-caption text-muted-foreground">
            <input type="checkbox" checked={hideEmpty} onChange={(e) => setHideEmpty(e.target.checked)} className="size-4 accent-primary" />
            Ẩn chương con chưa có câu
          </label>
          {over && <p role="alert" className="w-full text-caption font-semibold text-danger sm:w-auto">Tối đa {MAX_QUESTIONS} câu, bạn đang có {total}.</p>}
          <Button variant="ghost" leftIcon={<RotateCcw aria-hidden="true" />} onClick={() => setCells(initial)}>Đặt lại</Button>
          <Button variant="outline" onClick={onClose}>Huỷ</Button>
          <Button onClick={apply} disabled={over || total === 0}>Áp dụng ma trận</Button>
        </footer>
      </motion.div>
    </div>
  );
}

function Cell({ value, label, onChange }: { value: number; label: string; onChange: (n: number) => void }) {
  const onKey = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowUp') {
      e.preventDefault();
      onChange(value + 1);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      onChange(value - 1);
    }
  };
  return (
    <input
      inputMode="numeric"
      aria-label={label}
      value={value || ''}
      placeholder="·"
      onChange={(e) => onChange(Number(e.target.value.replace(/\D/g, '')))}
      onKeyDown={onKey}
      onFocus={(e) => e.target.select()}
      className={cn(
        'h-8 w-full min-w-8 rounded-md bg-transparent text-center text-label tabular-nums outline-none transition-colors placeholder:text-border hover:bg-surface-muted focus:bg-background focus:ring-2 focus:ring-ring',
        value ? 'bg-accent-subtle font-bold text-foreground' : 'text-muted-foreground',
      )}
    />
  );
}
