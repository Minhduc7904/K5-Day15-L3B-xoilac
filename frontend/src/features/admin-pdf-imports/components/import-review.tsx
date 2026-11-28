'use client';

/**
 * Trang /admin/pdf-imports/[id] (#11 dựng UI cho API của #3): xem phiên nhập, duyệt từng bản nháp.
 * Sửa nội dung/lựa chọn/đáp án/lời giải, chốt chương và độ khó (có nút dùng gợi ý), xác nhận đã kiểm hình,
 * rồi Duyệt (vào ngân hàng) hoặc Bỏ. Ảnh `media:ID` xem qua URL có ký của #3.
 */
import { ArrowLeft, Check, FileText, Save, X } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { MathContent, type MediaResolver } from '@/components/math/math-content';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Alert, Badge, Skeleton } from '@/components/ui/feedback';
import { FormField } from '@/components/ui/form-field';
import { Input, Textarea } from '@/components/ui/input';
import { useToast } from '@/components/ui/toast';
import { ConfirmModal, EmptyState, PageHeader, selectClass } from '@/features/admin/admin-ui';
import { cn } from '@/lib/cn';
import { toApiError, type ApiError } from '@/lib/api-error';
import { DRAFT_STATUS, FLAG_LABELS, IMPORT_STATUS, pdfImportsApi, type DraftEdit, type PdfDraft, type PdfImport } from '../api';

const MEDIA_RE = /media:(\d+)/g;
const TYPE_LABEL: Record<PdfDraft['type'], string> = {
  SINGLE_CHOICE: 'Một đáp án', MULTIPLE_CHOICE: 'Nhiều đáp án', TRUE_FALSE: 'Đúng/sai', SHORT_ANSWER: 'Trả lời ngắn', ESSAY: 'Tự luận',
};

export function ImportReviewPage({ id }: { id: number }) {
  const [row, setRow] = useState<PdfImport | null>(null);
  const [drafts, setDrafts] = useState<PdfDraft[] | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const toast = useToast();

  const load = useCallback(async () => {
    try {
      const r = await pdfImportsApi.get(id);
      setRow(r);
      setDrafts(r.status === 'ready_for_review' ? await pdfImportsApi.drafts(id) : []);
      setError(null);
    } catch (e) {
      setError(toApiError(e));
    }
  }, [id]);
  useEffect(() => {
    void load();
  }, [load]);
  useEffect(() => {
    if (!row || (row.status !== 'queued' && row.status !== 'processing')) return;
    const t = window.setInterval(() => void load(), 5000);
    return () => window.clearInterval(t);
  }, [row, load]);
  useEffect(() => {
    if (drafts?.length && selected === null) setSelected(drafts.find((d) => d.status === 'pending')?.id ?? drafts[0].id);
  }, [drafts, selected]);

  const openPdf = async () => {
    if (!row) return;
    try {
      const { url } = await pdfImportsApi.mediaUrl(id, row.originalMediaId);
      window.open(url, '_blank', 'noopener');
    } catch (e) {
      toast({ tone: 'danger', title: 'Không mở được PDF', description: toApiError(e).message });
    }
  };

  const back = <Button href="/admin/pdf-imports" size="sm" variant="ghost" leftIcon={<ArrowLeft aria-hidden="true" />}>Danh sách</Button>;
  if (error) return (<><PageHeader title="Phiên nhập PDF" actions={back} /><Alert tone="danger" title="Không tải được phiên nhập">{error.message}</Alert></>);
  if (!row || !drafts) return <Skeleton className="h-96 w-full" />;

  const current = drafts.find((d) => d.id === selected) ?? null;
  const counts = { pending: 0, approved: 0, rejected: 0 };
  drafts.forEach((d) => counts[d.status]++);

  return (
    <>
      <PageHeader
        title={row.filename}
        description={`${row.pageCount ?? '?'} trang · ${drafts.length} câu nháp · đã duyệt ${counts.approved}, đã bỏ ${counts.rejected}, còn ${counts.pending}`}
        actions={<>{back}<Button size="sm" variant="outline" leftIcon={<FileText aria-hidden="true" />} onClick={() => void openPdf()}>Xem PDF gốc</Button></>}
      />
      <div className="mb-4 flex flex-wrap gap-2">
        <Badge tone={IMPORT_STATUS[row.status]?.tone ?? 'neutral'} dot>{IMPORT_STATUS[row.status]?.label ?? row.status}</Badge>
        <Badge>Bước: {row.stage}</Badge>
      </div>
      {row.error && <Alert tone="danger" title="Phiên nhập lỗi" className="mb-4">{row.error}</Alert>}
      {row.warnings?.length ? (
        <Alert tone="warning" title="Cảnh báo" className="mb-4">
          <ul className="list-disc pl-5">{row.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
        </Alert>
      ) : null}
      {(row.status === 'queued' || row.status === 'processing') && (
        <Alert tone="info" title="Đang xử lý">Trang tự làm mới mỗi 5 giây cho tới khi có bản nháp.</Alert>
      )}
      {row.status === 'ready_for_review' && drafts.length === 0 && <EmptyState>Phiên này không có bản nháp nào.</EmptyState>}
      {drafts.length > 0 && (
        <div className="grid gap-6 lg:grid-cols-[16rem_minmax(0,1fr)] lg:items-start">
          <Card className="lg:sticky lg:top-6">
            <CardContent className="max-h-[70vh] overflow-y-auto p-2">
              <ul className="grid gap-1">
                {drafts.map((d) => (
                  <li key={d.id}>
                    <button type="button" onClick={() => setSelected(d.id)} aria-current={d.id === selected || undefined}
                      className={cn('flex w-full items-center justify-between gap-2 rounded-xl px-3 py-2 text-left text-label',
                        d.id === selected ? 'bg-primary-subtle text-primary' : 'hover:bg-surface-muted')}>
                      <span>Câu {d.number}{d.section ? ` · ${d.section}` : ''}</span>
                      <Badge tone={DRAFT_STATUS[d.status].tone}>{DRAFT_STATUS[d.status].label}</Badge>
                    </button>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
          {current && (
            <DraftEditor key={current.id} importId={id} draft={current}
              onChanged={(next) => setDrafts((list) => list?.map((d) => (d.id === next.id ? next : d)) ?? null)} />
          )}
        </div>
      )}
    </>
  );
}

function DraftEditor({ importId, draft, onChanged }: { importId: number; draft: PdfDraft; onChanged: (d: PdfDraft) => void }) {
  const toast = useToast();
  const [form, setForm] = useState(() => toForm(draft));
  const [busy, setBusy] = useState<'save' | 'approve' | 'reject' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [confirmReject, setConfirmReject] = useState(false);
  const [media, setMedia] = useState<Record<string, string>>({});
  const locked = draft.status !== 'pending';

  const ids = useMemo(() => {
    const text = [form.content, form.solution, ...form.statements.map((s) => s.content)].join('\n');
    return [...new Set([...text.matchAll(MEDIA_RE)].map((m) => m[1]))];
  }, [form]);
  useEffect(() => {
    const missing = ids.filter((m) => !media[m]);
    if (!missing.length) return;
    let cancelled = false;
    Promise.all(missing.map((m) => pdfImportsApi.mediaUrl(importId, Number(m)).then((r) => [m, r.url] as const).catch(() => null)))
      .then((pairs) => !cancelled && setMedia((prev) => ({ ...prev, ...Object.fromEntries(pairs.filter((p) => p !== null)) })));
    return () => {
      cancelled = true;
    };
  }, [ids, importId, media]);
  const resolver: MediaResolver = (mid) => (media[mid] ? { src: media[mid], alt: 'Hình từ PDF', width: 600, height: 400 } : undefined);

  const edit = (): DraftEdit => ({
    content: form.content,
    statements: form.statements,
    correctAnswer: form.correctAnswer.trim() || null,
    solution: form.solution.trim() || null,
    chapterCodes: form.chapterCodes.split(/[,\s]+/).map((c) => c.trim()).filter(Boolean),
    difficulty: form.difficulty || null,
    imageReviewed: form.imageReviewed,
  });

  const run = async (kind: 'save' | 'approve' | 'reject') => {
    setBusy(kind);
    setError(null);
    try {
      let next = draft;
      if (kind !== 'reject') next = await pdfImportsApi.edit(importId, draft.id, edit());
      if (kind === 'approve') next = await pdfImportsApi.approve(importId, draft.id);
      if (kind === 'reject') next = await pdfImportsApi.reject(importId, draft.id);
      onChanged(next);
      setForm(toForm(next));
      setConfirmReject(false);
      toast({
        tone: 'success',
        title: kind === 'save' ? 'Đã lưu bản nháp' : kind === 'approve' ? 'Đã duyệt vào ngân hàng' : 'Đã bỏ bản nháp',
        description: kind === 'approve' && next.questionId ? `Mã câu Q${String(next.questionId).padStart(5, '0')}` : undefined,
      });
    } catch (e) {
      setError(toApiError(e).message);
    } finally {
      setBusy(null);
    }
  };

  const set = (changes: Partial<ReturnType<typeof toForm>>) => setForm((f) => ({ ...f, ...changes }));
  const s = draft.suggestions;

  return (
    <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] 2xl:items-start">
      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
          <CardTitle>Câu {draft.number} · {TYPE_LABEL[draft.type]}</CardTitle>
          <div className="flex flex-wrap gap-1">
            <Badge tone={DRAFT_STATUS[draft.status].tone}>{DRAFT_STATUS[draft.status].label}</Badge>
            <Badge>Trang {draft.sourcePages.join(', ')}</Badge>
            <Badge tone={draft.answerState === 'confirmed' ? 'success' : 'warning'}>Đáp án: {draft.answerState}</Badge>
          </div>
        </CardHeader>
        <CardContent className="grid gap-4 pt-0">
          {draft.flags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {draft.flags.map((f) => <Badge key={f} tone="warning">{FLAG_LABELS[f] ?? f}</Badge>)}
            </div>
          )}
          {draft.questionId && <Alert tone="success" title={`Đã vào ngân hàng: Q${String(draft.questionId).padStart(5, '0')}`} />}
          {error && <Alert tone="danger" title="Không thực hiện được">{error}</Alert>}
          <fieldset disabled={locked} className="grid gap-4">
            <FormField label="Nội dung">
              {(f) => <Textarea {...f} rows={5} value={form.content} onChange={(e) => set({ content: e.target.value })} />}
            </FormField>
            {form.statements.length > 0 && (
              <div className="grid gap-2">
                <span className="text-label">{draft.type === 'TRUE_FALSE' ? 'Mệnh đề' : 'Lựa chọn'}</span>
                {form.statements.map((st, i) => (
                  <div key={i} className="flex items-center gap-2">
                    <b className="w-6 shrink-0 text-label">{draft.type === 'TRUE_FALSE' ? `${String.fromCharCode(97 + i)})` : `${String.fromCharCode(65 + i)}.`}</b>
                    <Input className="min-w-0" aria-label={`Lựa chọn ${i + 1}`} value={st.content}
                      onChange={(e) => set({ statements: form.statements.map((x, j) => (j === i ? { ...x, content: e.target.value } : x)) })} />
                    <select aria-label={`Đúng/sai lựa chọn ${i + 1}`} className={cn(selectClass, 'w-28 shrink-0')}
                      value={st.isCorrect === null ? '' : String(st.isCorrect)}
                      onChange={(e) => set({ statements: form.statements.map((x, j) => (j === i ? { ...x, isCorrect: e.target.value === '' ? null : e.target.value === 'true' } : x)) })}>
                      <option value="">Chưa rõ</option>
                      <option value="true">Đúng</option>
                      <option value="false">Sai</option>
                    </select>
                  </div>
                ))}
              </div>
            )}
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="Đáp án (trả lời ngắn)">
                {(f) => <Input {...f} value={form.correctAnswer} onChange={(e) => set({ correctAnswer: e.target.value })} />}
              </FormField>
              <FormField label="Độ khó" hint={s?.difficulty ? `Gợi ý: ${s.difficulty}` : undefined}>
                {(f) => (
                  <select {...f} className={selectClass} value={form.difficulty} onChange={(e) => set({ difficulty: e.target.value as typeof form.difficulty })}>
                    <option value="">Chưa chọn</option>
                    {['NB', 'TH', 'VD', 'VDC'].map((d) => <option key={d} value={d}>{d}</option>)}
                  </select>
                )}
              </FormField>
            </div>
            <FormField label="Mã chương" hint={s?.chapter ? `Gợi ý: ${[s.chapter, s.subchapter].filter(Boolean).join(', ')}` : 'Cách nhau bởi dấu phẩy, cùng một khối, vd 12C1, 12C11.'}>
              {(f) => <Input {...f} value={form.chapterCodes} onChange={(e) => set({ chapterCodes: e.target.value })} />}
            </FormField>
            {s?.chapter && (
              <div>
                <Button size="sm" variant="ghost" onClick={() => set({
                  chapterCodes: [s.chapter, s.subchapter].filter(Boolean).join(', '),
                  difficulty: (s.difficulty ?? form.difficulty) as typeof form.difficulty,
                })}>
                  Dùng nhãn gợi ý
                </Button>
              </div>
            )}
            <FormField label="Lời giải">
              {(f) => <Textarea {...f} rows={4} value={form.solution} onChange={(e) => set({ solution: e.target.value })} />}
            </FormField>
            <Checkbox label="Đã kiểm tra hình" description="Bắt buộc với câu có hình, phụ thuộc hình hoặc có cờ về hình."
              checked={form.imageReviewed} onChange={(e) => set({ imageReviewed: e.target.checked })} />
          </fieldset>
          {!locked && (
            <div className="flex flex-wrap justify-end gap-2">
              <Button variant="ghost" leftIcon={<X aria-hidden="true" />} disabled={busy !== null} onClick={() => setConfirmReject(true)}>Bỏ</Button>
              <Button variant="outline" loading={busy === 'save'} disabled={busy !== null} leftIcon={<Save aria-hidden="true" />} onClick={() => void run('save')}>Lưu</Button>
              <Button loading={busy === 'approve'} disabled={busy !== null} leftIcon={<Check aria-hidden="true" />} onClick={() => void run('approve')}>Lưu và duyệt</Button>
            </div>
          )}
        </CardContent>
      </Card>
      <Card className="2xl:sticky 2xl:top-6">
        <CardHeader><CardTitle>Xem trước</CardTitle></CardHeader>
        <CardContent className="grid gap-3 pt-0">
          <MathContent source={form.content} resolveMedia={resolver} />
          {form.statements.map((st, i) => (
            <p key={i} className={cn('flex gap-2 rounded-xl border px-3 py-2', st.isCorrect ? 'border-success/40 bg-success-subtle' : 'border-border')}>
              <b>{draft.type === 'TRUE_FALSE' ? `${String.fromCharCode(97 + i)})` : `${String.fromCharCode(65 + i)}.`}</b>
              <MathContent source={st.content} inline resolveMedia={resolver} />
            </p>
          ))}
          {form.solution && (
            <div className="rounded-xl bg-surface-muted p-3">
              <p className="mb-1 text-caption font-semibold text-muted-foreground uppercase">Lời giải</p>
              <MathContent source={form.solution} resolveMedia={resolver} className="text-body" />
            </div>
          )}
          {s?.neighbors?.length ? (
            <div className="grid gap-1 text-caption text-muted-foreground">
              <p className="font-semibold">Câu gần nhất trong ngân hàng</p>
              {s.neighbors.slice(0, 5).map((n) => (
                <p key={n.questionId}>Q{String(n.questionId).padStart(5, '0')} · {n.subchapter ?? n.chapter} · {n.difficulty} · {n.similarity.toFixed(2)}</p>
              ))}
            </div>
          ) : null}
        </CardContent>
      </Card>
      <ConfirmModal open={confirmReject} title="Bỏ bản nháp này?" description="Bản nháp bị đánh dấu đã bỏ và không vào ngân hàng câu hỏi."
        confirmLabel="Bỏ bản nháp" busy={busy === 'reject'} onConfirm={() => void run('reject')} onClose={() => setConfirmReject(false)} />
    </div>
  );
}

function toForm(d: PdfDraft) {
  return {
    content: d.content,
    statements: d.statements.map((s) => ({ ...s })),
    correctAnswer: d.correctAnswer ?? '',
    solution: d.solution ?? '',
    chapterCodes: d.chapterCodes.join(', '),
    difficulty: (d.difficulty ?? '') as '' | 'NB' | 'TH' | 'VD' | 'VDC',
    imageReviewed: d.imageReviewed,
  };
}
