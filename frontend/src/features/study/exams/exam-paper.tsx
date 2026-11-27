'use client';

import { Download, FileText, X } from 'lucide-react';
import { motion } from 'motion/react';
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { Skeleton } from '@/components/ui/feedback';
import { studyApi } from '../api';
import { QuestionContent } from '../components/question-content';
import type { Exam, PublicQuestion, QuestionType } from '../types';
import { useResource } from '../use-resource';

/*
 * Xem đề dạng giấy A4 và tải PDF.
 * Trang được chia bằng cách đo chiều cao từng khối (đầu đề, tiêu đề phần, từng câu) trong một vùng ẩn
 * có đúng bề rộng vùng in, rồi xếp lần lượt vào trang. "Tải PDF" mở hộp in của trình duyệt với khổ A4
 * (chọn "Lưu dưới dạng PDF"), nên chữ và công thức giữ dạng vector, in ra giấy vẫn nét.
 */

const MM = 96 / 25.4;
const PAGE_W = 210;
const PAGE_H = 297;
const PAD_X = 18;
const PAD_TOP = 16;
const PAD_BOTTOM = 22; // gồm chân trang
const CONTENT_H = (PAGE_H - PAD_TOP - PAD_BOTTOM) * MM;
const GAP = 14; // px giữa các khối

const ROMAN = ['I', 'II', 'III', 'IV'];
const PART_TITLE: Record<QuestionType, string> = {
  SINGLE_CHOICE: 'Câu trắc nghiệm nhiều phương án lựa chọn.',
  TRUE_FALSE: 'Câu trắc nghiệm đúng sai.',
  SHORT_ANSWER: 'Câu trắc nghiệm trả lời ngắn.',
};
const partHint = (type: QuestionType, n: number) =>
  type === 'SINGLE_CHOICE'
    ? `Thí sinh trả lời từ câu 1 đến câu ${n}. Mỗi câu hỏi thí sinh chỉ chọn một phương án.`
    : type === 'TRUE_FALSE'
      ? `Thí sinh trả lời từ câu 1 đến câu ${n}. Trong mỗi ý a), b), c), d) ở mỗi câu, thí sinh chọn đúng hoặc sai.`
      : `Thí sinh trả lời từ câu 1 đến câu ${n}.`;

type Block =
  | { key: string; kind: 'head' }
  | { key: string; kind: 'part'; index: number; type: QuestionType; count: number }
  | { key: string; kind: 'question'; n: number; q: PublicQuestion }
  | { key: string; kind: 'end' };

export function ExamPaperDialog({ examId, onClose }: { examId: string; onClose: () => void }) {
  const res = useResource(() => studyApi.getExam(examId), `exam-paper-${examId}`);
  const [mounted, setMounted] = useState(false);
  const [pageCount, setPageCount] = useState(0);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    setMounted(true);
    const prev = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => {
      document.body.style.overflow = overflow;
      window.removeEventListener('keydown', onKey);
      prev?.focus();
    };
  }, [onClose]);

  useEffect(() => {
    if (mounted) closeRef.current?.focus();
  }, [mounted]);

  const download = () => {
    if (res.status !== 'ready') return;
    const title = document.title;
    // Tên file PDF gợi ý lấy theo tiêu đề trang.
    document.title = res.data.exam.title;
    const restore = () => {
      document.title = title;
      window.removeEventListener('afterprint', restore);
    };
    window.addEventListener('afterprint', restore);
    window.print();
  };

  if (!mounted) return null;

  return createPortal(
    <div className="paper-root fixed inset-0 z-[70] flex flex-col" role="dialog" aria-modal="true" aria-labelledby="paper-title">
      <motion.div
        aria-hidden="true"
        className="paper-chrome absolute inset-0 bg-[rgb(8_15_30/0.86)] backdrop-blur-md"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        onClick={onClose}
      />

      <header className="paper-chrome relative z-10 flex items-center gap-3 border-b border-white/10 bg-[rgb(8_15_30/0.6)] px-4 py-3 text-white sm:px-6">
        <FileText className="size-5 shrink-0 text-white/70" aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <h2 id="paper-title" className="truncate text-label font-semibold">
            {res.status === 'ready' ? res.data.exam.title : 'Đang chuẩn bị đề…'}
          </h2>
          <p className="truncate text-caption text-white/60">
            Khổ A4{pageCount > 0 && ` · ${pageCount} trang`} · in ra để làm trên giấy
          </p>
        </div>
        <button
          type="button"
          onClick={download}
          disabled={res.status !== 'ready' || pageCount === 0}
          className="inline-flex h-10 items-center gap-2 rounded-xl bg-white px-4 text-label font-semibold text-primary transition-[background-color,transform] hover:bg-white/90 active:scale-[0.97] disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
        >
          <Download className="size-4" aria-hidden="true" />
          <span className="max-sm:sr-only">Tải PDF</span>
        </button>
        <button
          ref={closeRef}
          type="button"
          onClick={onClose}
          aria-label="Đóng xem đề"
          className="flex size-10 shrink-0 items-center justify-center rounded-xl text-white/80 transition-colors hover:bg-white/10 hover:text-white focus-visible:outline-2 focus-visible:outline-white"
        >
          <X className="size-5" aria-hidden="true" />
        </button>
      </header>

      <div className="paper-scroll relative z-0 min-h-0 flex-1 overflow-y-auto overscroll-contain" onClick={(e) => e.target === e.currentTarget && onClose()}>
        {res.status === 'loading' && (
          <div className="mx-auto mt-8 w-[min(794px,calc(100vw-2rem))]">
            <Skeleton className="aspect-[210/297] w-full rounded-sm bg-white/10" />
          </div>
        )}
        {res.status === 'error' && <p className="mt-16 text-center text-label text-white/80">Chưa tải được đề. Đóng lại và thử lần nữa nhé.</p>}
        {res.status === 'ready' && <Paper exam={res.data.exam} questions={res.data.questions} onPages={setPageCount} />}
      </div>
    </div>,
    document.body,
  );
}

function Paper({ exam, questions, onPages }: { exam: Exam; questions: PublicQuestion[]; onPages: (n: number) => void }) {
  const byId = new Map(questions.map((q) => [q.id, q]));
  const sections = exam.sections
    .map((s) => ({ ...s, qs: s.questionIds.map((id) => byId.get(id)).filter((q): q is PublicQuestion => Boolean(q)) }))
    .filter((s) => s.qs.length);
  const blocks: Block[] = [
    { key: 'head', kind: 'head' },
    ...sections.flatMap((s, i): Block[] => [
      { key: `part-${s.id}`, kind: 'part', index: i, type: s.type, count: s.qs.length },
      ...s.qs.map((q, k): Block => ({ key: `q-${s.id}-${q.id}`, kind: 'question', n: k + 1, q })),
    ]),
    { key: 'end', kind: 'end' },
  ];

  const measureRef = useRef<HTMLDivElement>(null);
  const [pages, setPages] = useState<Block[][] | null>(null);
  const [scale, setScale] = useState(1);
  const scrollerRef = useRef<HTMLDivElement>(null);

  const paginate = useCallback(() => {
    const root = measureRef.current;
    if (!root) return;
    const heights = new Map<string, number>();
    root.querySelectorAll<HTMLElement>('[data-block]').forEach((el) => heights.set(el.dataset.block!, el.getBoundingClientRect().height));
    const out: Block[][] = [[]];
    let used = 0;
    blocks.forEach((b, i) => {
      const h = heights.get(b.key) ?? 0;
      // Tiêu đề phần đi cùng câu đầu tiên của phần, không để mồ côi cuối trang.
      const need = b.kind === 'part' && blocks[i + 1] ? h + GAP + (heights.get(blocks[i + 1].key) ?? 0) : h;
      const add = (out[out.length - 1].length ? GAP : 0) + need;
      if (out[out.length - 1].length && used + add > CONTENT_H) {
        out.push([]);
        used = 0;
      }
      used += (out[out.length - 1].length ? GAP : 0) + h;
      out[out.length - 1].push(b);
    });
    setPages(out);
    onPages(out.length);
    // eslint-disable-next-line react-hooks/exhaustive-deps -- blocks dựng lại từ exam/questions
  }, [exam, questions, onPages]);

  // Đo sau khi font và ảnh tải xong để chiều cao đúng.
  useLayoutEffect(() => {
    let cancelled = false;
    const root = measureRef.current;
    if (!root) return;
    const imgs = [...root.querySelectorAll('img')].filter((img) => !img.complete);
    const loaded = imgs.map(
      (img) =>
        new Promise<void>((resolve) => {
          img.addEventListener('load', () => resolve(), { once: true });
          img.addEventListener('error', () => resolve(), { once: true });
        }),
    );
    Promise.all([document.fonts?.ready, ...loaded]).then(() => {
      if (!cancelled) paginate();
    });
    return () => {
      cancelled = true;
    };
  }, [paginate]);

  // Thu nhỏ trang cho vừa màn hình hẹp.
  useEffect(() => {
    const el = scrollerRef.current;
    if (!el) return;
    const fit = () => setScale(Math.min(1, (el.clientWidth - 32) / (PAGE_W * MM)));
    fit();
    const ro = new ResizeObserver(fit);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  return (
    <div ref={scrollerRef} className="paper-pages grid justify-items-center gap-6 px-4 py-6 sm:py-8">
      {/* Vùng đo ẩn: cùng bề rộng vùng in. */}
      <div
        ref={measureRef}
        aria-hidden="true"
        className="paper-measure exam-paper pointer-events-none invisible fixed top-0 left-0 grid"
        style={{ width: `${PAGE_W - 2 * PAD_X}mm` }}
      >
        {blocks.map((b) => (
          <div key={b.key} data-block={b.key} className="pb-px">
            <BlockView block={b} exam={exam} total={questions.length} />
          </div>
        ))}
      </div>

      {!pages && <Skeleton className="aspect-[210/297] w-[min(794px,calc(100vw-2rem))] rounded-sm bg-white/10" />}
      {pages?.map((blocksOnPage, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: Math.min(i, 4) * 0.06, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
          className="paper-slot"
          style={{ width: PAGE_W * MM * scale, height: PAGE_H * MM * scale }}
        >
          <article
            aria-label={`Trang ${i + 1} trên ${pages.length}`}
            className="paper-page exam-paper relative origin-top-left bg-white shadow-[0_18px_50px_rgb(0_0_0/0.45)]"
            style={{
              width: `${PAGE_W}mm`,
              height: `${PAGE_H}mm`,
              padding: `${PAD_TOP}mm ${PAD_X}mm ${PAD_BOTTOM}mm`,
              transform: scale < 1 ? `scale(${scale})` : undefined,
            }}
          >
            <div className="grid" style={{ rowGap: GAP }}>
              {blocksOnPage.map((b) => (
                <BlockView key={b.key} block={b} exam={exam} total={questions.length} pageCount={pages.length} />
              ))}
            </div>
            <footer className="absolute inset-x-0 bottom-0 flex items-center justify-between border-t border-black/15 text-[11px] text-black/55" style={{ margin: `0 ${PAD_X}mm 9mm`, paddingTop: '2mm' }}>
              <span className="truncate pr-4">Examind · {exam.title}</span>
              <span className="shrink-0 tabular-nums">Trang {i + 1}/{pages.length}</span>
            </footer>
          </article>
        </motion.div>
      ))}
    </div>
  );
}

function BlockView({ block, exam, total, pageCount }: { block: Block; exam: Exam; total: number; pageCount?: number }) {
  if (block.kind === 'head') return <PaperHead exam={exam} total={total} pageCount={pageCount} />;
  if (block.kind === 'end') return <p className="pt-2 text-center text-[14px] font-bold tracking-[0.3em]">------ HẾT ------</p>;
  if (block.kind === 'part') {
    return (
      <div className="text-[15px] leading-snug">
        <p>
          <b>PHẦN {ROMAN[block.index]}. {PART_TITLE[block.type]}</b>{' '}
          <span>{partHint(block.type, block.count)}</span>
        </p>
      </div>
    );
  }
  return <PaperQuestion n={block.n} q={block.q} />;
}

function PaperHead({ exam, total, pageCount }: { exam: Exam; total: number; pageCount?: number }) {
  const time = exam.durationMinutes > 0 ? `Thời gian làm bài: ${exam.durationMinutes} phút` : 'Không giới hạn thời gian làm bài';
  return (
    <div className="grid gap-4 text-[14px]">
      <div className="grid grid-cols-[38%_1fr] gap-4 text-center leading-snug">
        <div className="grid content-start justify-items-center gap-0.5">
          <b className="tracking-wide">EXAMIND</b>
          <span>Đề luyện tập cá nhân</span>
          <span className="mt-1 h-px w-20 bg-black" />
          <i className="mt-1 text-[13px]">(Đề có {total} câu{pageCount ? `, ${pageCount} trang` : ''})</i>
        </div>
        <div className="grid content-start justify-items-center gap-0.5">
          <b>ĐỀ LUYỆN TẬP MÔN TOÁN</b>
          <b className="text-balance">{exam.title.toLocaleUpperCase('vi')}</b>
          <i>{time}</i>
          <span className="mt-1 h-px w-24 bg-black" />
        </div>
      </div>
      <div className="grid grid-cols-[1fr_auto] gap-x-6 gap-y-1.5 text-[14px]">
        <Dotted label="Họ và tên học sinh:" />
        <Dotted label="Lớp:" short />
        <Dotted label="Ngày làm:" />
        <Dotted label="Điểm:" short />
      </div>
    </div>
  );
}

function Dotted({ label, short }: { label: string; short?: boolean }) {
  return (
    <p className={short ? 'flex w-40 items-end gap-1' : 'flex items-end gap-1'}>
      <span className="shrink-0">{label}</span>
      <span className="mb-[3px] flex-1 border-b border-dotted border-black/70" />
    </p>
  );
}

function PaperQuestion({ n, q }: { n: number; q: PublicQuestion }) {
  const longest = Math.max(0, ...q.statements.map((s) => s.content.replace(/\$|\\[a-z]+|[{}]/gi, '').length));
  const hasImg = q.statements.some((s) => s.content.includes('media:'));
  const cols = q.type !== 'SINGLE_CHOICE' ? 1 : hasImg ? 2 : longest <= 14 ? 4 : longest <= 34 ? 2 : 1;

  return (
    <div className="grid gap-1.5 text-[15px] leading-normal">
      <div className="paper-q flex gap-1.5">
        <b className="shrink-0">Câu {n}.</b>
        <QuestionContent source={q.content} printable className="min-w-0 flex-1" />
      </div>
      {q.statements.length > 0 && (
        <div className="grid gap-x-4 gap-y-1 pl-[3.25rem]" style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}>
          {q.statements.map((s) => (
            <p key={s.label} className="flex gap-1.5">
              <b className="shrink-0">{q.type === 'SINGLE_CHOICE' ? `${s.label}.` : `${s.label})`}</b>
              <QuestionContent source={s.content} inline printable />
            </p>
          ))}
        </div>
      )}
      {q.type === 'SHORT_ANSWER' && <AnswerBoxes />}
    </div>
  );
}

/** Ô điền đáp án trả lời ngắn như phiếu thi (4 ô ký tự). */
function AnswerBoxes() {
  return (
    <p className="flex items-center gap-2 pl-[3.25rem] text-[13px]">
      <span>Đáp án:</span>
      {Array.from({ length: 4 }, (_, i) => (
        <span key={i} className="inline-block size-6 border border-black/70" />
      ))}
    </p>
  );
}
