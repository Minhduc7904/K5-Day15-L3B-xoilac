'use client';

import { ChevronDown, Infinity as InfinityIcon, Lightbulb, Minus, Plus, Sparkles, Table2, Wand2, X } from 'lucide-react';
import { AnimatePresence, motion } from 'motion/react';
import { useId } from 'react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/cn';
import { chapterOf, difficultyLabels, typeLabels } from '../fixtures/chapters';
import type { Difficulty, QuestionType, StructureProposal } from '../types';
import { DIFFS, MAX_QUESTIONS, distribute, parentChapters, planFromRows, planTotal, rescaleChapters, rescaleTypes, TYPES, type ExamPlan } from './plan';
import { SegmentSlider } from './segment-slider';

const DURATIONS = [15, 20, 30, 45, 60, 90, 0];

export const typeColor: Record<QuestionType, string> = {
  SINGLE_CHOICE: 'bg-primary',
  TRUE_FALSE: 'bg-accent',
  SHORT_ANSWER: 'bg-ember',
  MULTIPLE_CHOICE: 'bg-info',
  ESSAY: 'bg-warning',
};
export const diffColor: Record<Difficulty, string> = {
  NB: 'bg-success',
  TH: 'bg-info',
  VD: 'bg-warning',
  VDC: 'bg-danger',
};
const typeShort: Record<QuestionType, string> = { SINGLE_CHOICE: 'Trắc nghiệm', TRUE_FALSE: 'Đúng sai', SHORT_ANSWER: 'Trả lời ngắn', MULTIPLE_CHOICE: 'Nhiều đáp án', ESSAY: 'Tự luận' };

interface Props {
  proposal: StructureProposal;
  /** Kế hoạch đã chỉnh mà agent chưa phân bổ lại. `null` khi ma trận khớp với tổng quan. */
  draft: ExamPlan | null;
  busy: boolean;
  built: boolean;
  onProposalChange: (next: StructureProposal) => void;
  onDraftChange: (plan: ExamPlan) => void;
  onCreate: () => void;
  onRebalance: () => void;
  onAdvanced: () => void;
}

/** Bảng chỉnh nhanh cấu trúc đề: thời gian, số câu mỗi chương cha, số câu mỗi dạng, tỉ lệ độ khó. */
export function StructurePreview({ proposal, draft, busy, built, onProposalChange, onDraftChange, onCreate, onRebalance, onAdvanced }: Props) {
  const plan = draft ?? planFromRows(proposal.rows);
  const total = planTotal(plan);
  const locked = built || busy;
  const addId = useId();

  const setChapter = (code: string, count: number) => {
    const others = plan.chapters.filter((c) => c.code !== code).reduce((s, c) => s + c.count, 0);
    const next = Math.max(0, Math.min(count, MAX_QUESTIONS - others));
    const chapters = plan.chapters.map((c) => (c.code === code ? { ...c, count: next } : c));
    const sum = chapters.reduce((s, c) => s + c.count, 0);
    onDraftChange({ ...plan, chapters, types: rescaleTypes(plan.types, sum) });
  };
  const removeChapter = (code: string) => {
    const chapters = plan.chapters.filter((c) => c.code !== code);
    const sum = chapters.reduce((s, c) => s + c.count, 0);
    onDraftChange({ ...plan, chapters, types: rescaleTypes(plan.types, sum) });
  };
  const addChapter = (code: string) => {
    if (!code || total >= MAX_QUESTIONS) return;
    const chapters = [...plan.chapters, { code, count: 1 }];
    onDraftChange({ ...plan, chapters, types: rescaleTypes(plan.types, total + 1) });
  };

  const typeValues = TYPES.reduce<number[]>((acc, t) => [...acc, (acc.at(-1) ?? 0) + plan.types[t]], []);
  const setTypes = (values: number[]) => {
    const types = Object.fromEntries(TYPES.map((t, i) => [t, values[i] - (i ? values[i - 1] : 0)])) as ExamPlan['types'];
    const sum = values.at(-1) ?? 0;
    onDraftChange({ ...plan, types, chapters: rescaleChapters(plan.chapters, sum) });
  };

  const diffValues = DIFFS.slice(0, -1).reduce<number[]>((acc, d) => [...acc, (acc.at(-1) ?? 0) + plan.difficulty[d]], []);
  const setDiffs = (values: number[]) => {
    const bounds = [0, ...values, 100];
    const difficulty = Object.fromEntries(DIFFS.map((d, i) => [d, bounds[i + 1] - bounds[i]])) as ExamPlan['difficulty'];
    onDraftChange({ ...plan, difficulty });
  };
  const diffCounts = distribute(total, DIFFS.map((d) => plan.difficulty[d]));

  const unused = parentChapters.filter((c) => !plan.chapters.some((p) => p.code === c.code));

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="min-h-0 flex-1 space-y-5 overflow-x-hidden overflow-y-auto px-4 pt-1 pb-4">
        {/* Thời gian */}
        <fieldset disabled={locked}>
          <legend className="mb-2 text-caption font-semibold text-foreground">Thời gian làm bài</legend>
          <div className="grid grid-cols-7 gap-1 rounded-xl bg-surface p-1">
            {DURATIONS.map((m) => {
              const on = proposal.durationMinutes === m;
              return (
                <label
                  key={m}
                  title={m ? `${m} phút` : 'Không giới hạn thời gian'}
                  className={cn(
                    'flex h-8 items-center justify-center rounded-lg text-caption font-semibold tabular-nums transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-ring',
                    on ? 'bg-background text-foreground shadow-soft' : 'text-muted-foreground hover:text-foreground',
                    locked ? 'cursor-not-allowed' : 'cursor-pointer',
                  )}
                >
                  <input type="radio" name="duration" value={m} checked={on} onChange={() => onProposalChange({ ...proposal, durationMinutes: m })} className="sr-only" />
                  {m ? m : <InfinityIcon className="size-4" aria-label="Không giới hạn" />}
                </label>
              );
            })}
          </div>
          <p className="mt-1.5 text-caption text-muted-foreground">
            {proposal.durationMinutes ? `${proposal.durationMinutes} phút, hết giờ bài tự nộp.` : 'Không giới hạn, làm xong thì tự nộp.'}
          </p>
        </fieldset>

        {/* Chương */}
        <section aria-labelledby="plan-chapters">
          <div className="mb-1.5 flex items-baseline justify-between">
            <h3 id="plan-chapters" className="text-caption font-semibold text-foreground">Số câu mỗi chương</h3>
            <span className="text-caption text-muted-foreground tabular-nums">{total}/{MAX_QUESTIONS} câu</span>
          </div>
          <ul className="divide-y divide-border rounded-xl border border-border">
            <AnimatePresence initial={false}>
              {plan.chapters.map(({ code, count }) => {
                const chapter = chapterOf(code);
                return (
                  <motion.li
                    key={code}
                    layout
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="group flex items-center gap-2 py-1.5 pr-1.5 pl-3"
                  >
                    <span className="min-w-0 flex-1">
                      <span className="line-clamp-2 text-label leading-snug font-medium text-foreground">{chapter.name}</span>
                      <span className="text-[0.6875rem] text-muted-foreground">Lớp {chapter.grade}</span>
                    </span>
                    <Stepper value={count} disabled={locked} canAdd={total < MAX_QUESTIONS} label={chapter.name} onChange={(n) => setChapter(code, n)} />
                    <button
                      type="button"
                      disabled={locked || plan.chapters.length <= 1}
                      onClick={() => removeChapter(code)}
                      aria-label={`Bỏ chương ${chapter.name}`}
                      className="flex size-7 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-danger-subtle hover:text-danger focus-visible:outline-2 focus-visible:outline-ring disabled:invisible"
                    >
                      <X className="size-3.5" aria-hidden="true" />
                    </button>
                  </motion.li>
                );
              })}
            </AnimatePresence>
          </ul>
          {!locked && unused.length > 0 && (
            <div className="relative mt-1.5">
              <label htmlFor={addId} className="sr-only">Thêm chương</label>
              <Plus className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-primary" aria-hidden="true" />
              <select
                id={addId}
                value=""
                disabled={total >= MAX_QUESTIONS}
                onChange={(e) => addChapter(e.target.value)}
                className="h-9 w-full appearance-none rounded-xl border border-dashed border-input bg-background pr-8 pl-9 text-label font-medium text-primary hover:border-primary focus-visible:outline-2 focus-visible:outline-ring disabled:opacity-50"
              >
                <option value="">{total >= MAX_QUESTIONS ? 'Đã đủ 30 câu' : 'Thêm chương'}</option>
                {([10, 11, 12] as const).map((g) => (
                  <optgroup key={g} label={`Lớp ${g}`}>
                    {unused.filter((c) => c.grade === g).map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
                  </optgroup>
                ))}
              </select>
              <ChevronDown className="pointer-events-none absolute top-1/2 right-3 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden="true" />
            </div>
          )}
        </section>

        {/* Dạng câu */}
        <section aria-labelledby="plan-types">
          <div className="mb-1 flex items-baseline justify-between">
            <h3 id="plan-types" className="text-caption font-semibold text-foreground">Dạng câu</h3>
            <span className="text-caption text-muted-foreground">Kéo vạch cuối để đổi tổng</span>
          </div>
          <SegmentSlider
            label="Số câu mỗi dạng"
            max={MAX_QUESTIONS}
            values={typeValues}
            minLast={1}
            disabled={locked}
            segments={TYPES.map((t) => ({ label: typeLabels[t], color: typeColor[t] }))}
            valueText={(i, v) => `${typeShort[TYPES[i]]}: ${v[i] - (i ? v[i - 1] : 0)} câu`}
            onChange={setTypes}
          />
          <Legend
            items={TYPES.map((t) => ({ key: t, color: typeColor[t], label: typeShort[t], value: `${plan.types[t]}` }))}
          />
        </section>

        {/* Độ khó */}
        <section aria-labelledby="plan-diff">
          <div className="mb-1 flex items-baseline justify-between">
            <h3 id="plan-diff" className="text-caption font-semibold text-foreground">Độ khó</h3>
            <span className="text-caption text-muted-foreground">Theo % số câu</span>
          </div>
          <SegmentSlider
            label="Tỉ lệ độ khó"
            max={100}
            step={5}
            values={diffValues}
            disabled={locked}
            segments={DIFFS.map((d) => ({ label: difficultyLabels[d], color: diffColor[d] }))}
            valueText={(i, v) => `${difficultyLabels[DIFFS[i]]}: ${v[i] - (i ? v[i - 1] : 0)}%`}
            onChange={setDiffs}
          />
          <Legend
            items={DIFFS.map((d, i) => ({ key: d, color: diffColor[d], label: difficultyLabels[d], value: `${plan.difficulty[d]}%`, hint: `${diffCounts[i]} câu` }))}
          />
        </section>

        <details className="group rounded-xl bg-warning-subtle px-3 py-2 text-caption text-foreground">
          <summary className="flex cursor-pointer list-none items-center gap-2 font-semibold">
            <Lightbulb className="size-4 shrink-0 text-warning" aria-hidden="true" />
            Vì sao cấu trúc này?
            <ChevronDown className="ml-auto size-4 transition-transform group-open:rotate-180" aria-hidden="true" />
          </summary>
          <p className="mt-1.5 pl-6">{proposal.reason}</p>
        </details>
      </div>

      {!built && (
        <div className="grid gap-2 border-t border-border bg-background px-4 pt-3 pb-4">
          <AnimatePresence initial={false}>
            {draft && (
              <motion.p
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="text-caption text-muted-foreground"
              >
                Bạn vừa chỉnh tổng quan. Agent sẽ chia lại số câu cho từng chương con trước khi tạo đề.
              </motion.p>
            )}
          </AnimatePresence>
          <div className="grid grid-cols-[auto_minmax(0,1fr)] gap-2">
            <Button variant="outline" leftIcon={<Table2 aria-hidden="true" />} onClick={onAdvanced} disabled={busy}>
              Nâng cao
            </Button>
            {draft ? (
              <Button leftIcon={<Sparkles aria-hidden="true" />} onClick={onRebalance} loading={busy} disabled={total === 0}>
                Để agent phân bổ lại
              </Button>
            ) : (
              <Button leftIcon={<Wand2 aria-hidden="true" />} onClick={onCreate} loading={busy} disabled={total === 0}>
                {busy ? 'Đang tạo…' : `Tạo đề ${total} câu`}
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function Legend({ items }: { items: Array<{ key: string; color: string; label: string; value: string; hint?: string }> }) {
  return (
    <ul className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
      {items.map((item) => (
        <li key={item.key} className="flex items-center gap-1.5 text-caption whitespace-nowrap">
          <i className={cn('size-2.5 shrink-0 rounded-full', item.color)} aria-hidden="true" />
          <span className="text-muted-foreground">{item.label}</span>
          <b className="font-semibold text-foreground tabular-nums">{item.value}</b>
          {item.hint && <span className="text-muted-foreground tabular-nums">· {item.hint}</span>}
        </li>
      ))}
    </ul>
  );
}

function Stepper({ value, disabled, canAdd, label, onChange }: { value: number; disabled?: boolean; canAdd: boolean; label: string; onChange: (v: number) => void }) {
  const btn =
    'flex size-7 items-center justify-center rounded-md text-foreground transition-colors hover:bg-surface-muted focus-visible:outline-2 focus-visible:outline-ring disabled:cursor-not-allowed disabled:opacity-35';
  return (
    <div className="flex shrink-0 items-center rounded-lg bg-surface p-0.5" role="group" aria-label={`Số câu chương ${label}`}>
      <button type="button" className={btn} aria-label="Bớt 1 câu" disabled={disabled || value <= 0} onClick={() => onChange(value - 1)}>
        <Minus className="size-3.5" aria-hidden="true" />
      </button>
      <output aria-live="polite" className="w-6 text-center text-label font-bold text-foreground tabular-nums">{value}</output>
      <button type="button" className={btn} aria-label="Thêm 1 câu" disabled={disabled || !canAdd} onClick={() => onChange(value + 1)}>
        <Plus className="size-3.5" aria-hidden="true" />
      </button>
    </div>
  );
}
