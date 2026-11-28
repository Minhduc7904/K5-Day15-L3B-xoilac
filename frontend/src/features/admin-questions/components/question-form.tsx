'use client';

/**
 * Trang /admin/questions/new và /admin/questions/[id]/edit (#11).
 * Form: nội dung (LaTeX `$…$`, ảnh `![mô tả](media:ID)`), loại câu, lựa chọn/mệnh đề với nút chọn đáp án đúng,
 * đáp án, lời giải, chương, độ khó, khối, trạng thái; ô xem trước hiển thị như học sinh thấy.
 * Luật kiểm ở validation.ts (bản sao luật backend); lỗi từ API hiện nguyên văn.
 */
import { ArrowLeft, ImagePlus, Plus, Save, Trash } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Button, IconButton } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, Skeleton } from '@/components/ui/feedback';
import { FormField } from '@/components/ui/form-field';
import { Input, Textarea } from '@/components/ui/input';
import { useToast } from '@/components/ui/toast';
import { PageHeader, selectClass } from '@/features/admin/admin-ui';
import { adminChaptersApi, chapterLabel, flattenTree, type ChapterNode } from '@/features/admin-chapters/api';
import { cn } from '@/lib/cn';
import { toApiError } from '@/lib/api-error';
import { adminQuestionsApi } from '../api';
import {
  DIFFICULTIES, GRADES, QUESTION_TYPES,
  type Difficulty, type QuestionDetail, type QuestionInput, type QuestionType, type StatementInput, type Visibility,
} from '../types';
import { usesStatements, validateQuestion } from '../validation';
import { optionLabel, QuestionView } from './question-view';

const EMPTY: QuestionInput = {
  content: '',
  type: 'SINGLE_CHOICE',
  difficulty: 'TH',
  grade: 12,
  visibility: 'PUBLISHED',
  correct_answer: null,
  solution: null,
  statements: [0, 1, 2, 3].map(() => ({ content: '', is_correct: false })),
  chapter_ids: [],
};

const fromDetail = (q: QuestionDetail): QuestionInput => ({
  content: q.content,
  type: q.type,
  difficulty: q.difficulty,
  grade: q.grade,
  visibility: q.visibility,
  correct_answer: q.correct_answer,
  solution: q.solution,
  statements: q.statements.map((s) => ({ statement_id: s.statement_id, content: s.content, is_correct: s.is_correct })),
  chapter_ids: q.chapters.map((c) => c.chapter_id),
});

export function QuestionFormPage({ id }: { id?: number }) {
  const router = useRouter();
  const toast = useToast();
  const [form, setForm] = useState<QuestionInput | null>(id ? null : EMPTY);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [tree, setTree] = useState<ChapterNode[] | null>(null);
  const [treeError, setTreeError] = useState<string | null>(null);
  const contentRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    adminQuestionsApi.get(id)
      .then((q) => !cancelled && setForm(fromDetail(q)))
      .catch((e) => !cancelled && setLoadError(toApiError(e).message));
    return () => {
      cancelled = true;
    };
  }, [id]);

  useEffect(() => {
    let cancelled = false;
    adminChaptersApi.tree()
      .then((t) => !cancelled && setTree(t))
      .catch((e) => !cancelled && setTreeError(toApiError(e).message));
    return () => {
      cancelled = true;
    };
  }, []);

  const problem = useMemo(() => (form ? validateQuestion(form) : null), [form]);

  if (loadError) return <Alert tone="danger" title="Không tải được câu hỏi">{loadError}</Alert>;
  if (!form) return <Skeleton className="h-96 w-full" />;

  const set = (changes: Partial<QuestionInput>) => setForm((f) => (f ? { ...f, ...changes } : f));
  const setStatement = (index: number, changes: Partial<StatementInput>) =>
    set({ statements: form.statements.map((s, i) => (i === index ? { ...s, ...changes } : s)) });
  const markCorrect = (index: number, value: boolean) =>
    set({
      statements: form.statements.map((s, i) =>
        form.type === 'SINGLE_CHOICE' ? { ...s, is_correct: i === index } : i === index ? { ...s, is_correct: value } : s,
      ),
    });

  const changeType = (type: QuestionType) => {
    const keep = usesStatements(type);
    const statements = keep
      ? (form.statements.length ? form.statements : EMPTY.statements).map((s, i) =>
          type === 'SINGLE_CHOICE' ? { ...s, is_correct: s.is_correct && form.statements.findIndex((x) => x.is_correct) === i } : s)
      : [];
    set({ type, statements });
  };

  const insertImage = async (file: File) => {
    setUploading(true);
    try {
      const { media_id } = await adminQuestionsApi.uploadImage(file);
      const tag = `\n![Hình](media:${media_id})\n`;
      const el = contentRef.current;
      const at = el ? el.selectionStart : form.content.length;
      set({ content: form.content.slice(0, at) + tag + form.content.slice(at) });
      toast({ tone: 'success', title: 'Đã tải ảnh lên', description: `Đã chèn media:${media_id} vào nội dung.` });
    } catch (e) {
      toast({ tone: 'danger', title: 'Không tải được ảnh', description: toApiError(e).message });
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const save = async () => {
    setTouched(true);
    if (problem) return;
    setSaving(true);
    setError(null);
    const body: QuestionInput = {
      ...form,
      correct_answer: form.correct_answer?.trim() || null,
      solution: form.solution?.trim() || null,
    };
    try {
      const saved = id ? await adminQuestionsApi.update(id, body) : await adminQuestionsApi.create(body);
      toast({ tone: 'success', title: id ? 'Đã lưu câu hỏi' : 'Đã tạo câu hỏi', description: saved.code });
      router.push(`/admin/questions/${saved.question_id}`);
    } catch (e) {
      const err = toApiError(e);
      setError(err.fieldErrors ? Object.values(err.fieldErrors).join(' ') || err.message : err.message);
    } finally {
      setSaving(false);
    }
  };

  const gradeChapters = tree ? flattenTree(tree.filter((r) => !form.grade || r.grade === form.grade)) : [];

  return (
    <>
      <PageHeader
        title={id ? 'Sửa câu hỏi' : 'Thêm câu hỏi'}
        actions={
          <>
            <Button href={id ? `/admin/questions/${id}` : '/admin/questions'} size="sm" variant="ghost" leftIcon={<ArrowLeft aria-hidden="true" />}>
              Quay lại
            </Button>
            <Button size="sm" loading={saving} leftIcon={<Save aria-hidden="true" />} onClick={() => void save()}>
              {id ? 'Lưu thay đổi' : 'Tạo câu hỏi'}
            </Button>
          </>
        }
      />
      {touched && problem && <Alert tone="warning" title={problem} className="mb-4" />}
      {error && <Alert tone="danger" title="Không lưu được câu hỏi" className="mb-4">{error}</Alert>}

      <div className="grid gap-6 2xl:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] 2xl:items-start">
        <Card>
          <CardContent className="grid gap-5">
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <FormField label="Loại câu" required>
                {(f) => (
                  <select {...f} className={selectClass} value={form.type} onChange={(e) => changeType(e.target.value as QuestionType)}>
                    {Object.entries(QUESTION_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                  </select>
                )}
              </FormField>
              <FormField label="Khối">
                {(f) => (
                  <select {...f} className={selectClass} value={form.grade ?? ''}
                    onChange={(e) => set({ grade: e.target.value ? Number(e.target.value) : null, chapter_ids: [] })}>
                    <option value="">Theo chương</option>
                    {GRADES.map((g) => <option key={g} value={g}>Lớp {g}</option>)}
                  </select>
                )}
              </FormField>
              <FormField label="Độ khó">
                {(f) => (
                  <select {...f} className={selectClass} value={form.difficulty ?? ''}
                    onChange={(e) => set({ difficulty: (e.target.value || null) as Difficulty | null })}>
                    <option value="">Chưa gắn</option>
                    {Object.entries(DIFFICULTIES).map(([k, v]) => <option key={k} value={k}>{k} · {v}</option>)}
                  </select>
                )}
              </FormField>
              <FormField label="Trạng thái duyệt" hint="Chỉ “Đã duyệt” mới được dùng dựng đề.">
                {(f) => (
                  <select {...f} className={selectClass} value={form.visibility} onChange={(e) => set({ visibility: e.target.value as Visibility })}>
                    <option value="PUBLISHED">Đã duyệt</option>
                    <option value="DRAFT">Nháp</option>
                    <option value="PRIVATE">Riêng tư</option>
                  </select>
                )}
              </FormField>
            </div>

            <FormField label="Nội dung" required hint="Công thức trong dòng $…$, riêng dòng $$…$$; ảnh ![mô tả](media:ID).">
              {(f) => (
                <Textarea {...f} ref={contentRef} rows={6} value={form.content} invalid={touched && !form.content.trim()}
                  onChange={(e) => set({ content: e.target.value })} />
              )}
            </FormField>
            <div>
              <input ref={fileRef} type="file" accept="image/png,image/jpeg,image/webp,image/gif" className="sr-only" id="question-image"
                onChange={(e) => e.target.files?.[0] && void insertImage(e.target.files[0])} />
              <Button size="sm" variant="outline" loading={uploading} leftIcon={<ImagePlus aria-hidden="true" />} onClick={() => fileRef.current?.click()}>
                Tải ảnh và chèn
              </Button>
            </div>

            {usesStatements(form.type) && (
              <fieldset className="grid gap-2">
                <legend className="mb-1 text-label">
                  {form.type === 'TRUE_FALSE' ? 'Mệnh đề (đánh dấu Đúng/Sai)' : form.type === 'SINGLE_CHOICE' ? 'Lựa chọn (chọn 1 đáp án đúng)' : 'Lựa chọn (đánh dấu các đáp án đúng)'}
                </legend>
                {form.statements.map((s, i) => (
                  <div key={s.statement_id ?? `new-${i}`} className="flex items-start gap-2">
                    <span className="mt-3 w-6 shrink-0 text-label font-semibold">{optionLabel(form.type, i)}</span>
                    <Input className="min-w-0" aria-label={`Nội dung ${optionLabel(form.type, i)}`} value={s.content}
                      invalid={touched && !s.content.trim()} onChange={(e) => setStatement(i, { content: e.target.value })} />
                    {form.type === 'TRUE_FALSE' ? (
                      <div className="flex shrink-0 overflow-hidden rounded-xl border border-input" role="group" aria-label={`Đúng/sai ${optionLabel(form.type, i)}`}>
                        {[true, false].map((v) => (
                          <button key={String(v)} type="button" aria-pressed={s.is_correct === v} onClick={() => markCorrect(i, v)}
                            className={cn('h-11 px-3 text-label', s.is_correct === v ? (v ? 'bg-success text-primary-foreground' : 'bg-danger text-primary-foreground') : 'hover:bg-surface-muted')}>
                            {v ? 'Đúng' : 'Sai'}
                          </button>
                        ))}
                      </div>
                    ) : (
                      <label className="flex h-11 shrink-0 cursor-pointer items-center gap-2 rounded-xl border border-input px-3 text-label">
                        <input
                          type={form.type === 'SINGLE_CHOICE' ? 'radio' : 'checkbox'}
                          name="correct-option"
                          checked={s.is_correct}
                          onChange={(e) => markCorrect(i, e.target.checked)}
                          className="size-4 accent-[var(--color-primary)]"
                        />
                        Đúng
                      </label>
                    )}
                    <IconButton label={`Xoá ${optionLabel(form.type, i)}`} onClick={() => set({ statements: form.statements.filter((_, j) => j !== i) })}>
                      <Trash aria-hidden="true" />
                    </IconButton>
                  </div>
                ))}
                {form.statements.length < 12 && (
                  <div>
                    <Button size="sm" variant="ghost" leftIcon={<Plus aria-hidden="true" />}
                      onClick={() => set({ statements: [...form.statements, { content: '', is_correct: false }] })}>
                      Thêm {form.type === 'TRUE_FALSE' ? 'mệnh đề' : 'lựa chọn'}
                    </Button>
                  </div>
                )}
              </fieldset>
            )}

            <FormField
              label="Đáp án"
              required={form.type === 'SHORT_ANSWER'}
              hint={usesStatements(form.type) ? 'Để trống thì tự suy từ lựa chọn đúng (vd “AC”, “ĐSĐS”).' : undefined}
            >
              {(f) => (
                <Input {...f} value={form.correct_answer ?? ''} maxLength={2000}
                  invalid={touched && form.type === 'SHORT_ANSWER' && !form.correct_answer?.trim()}
                  onChange={(e) => set({ correct_answer: e.target.value })} />
              )}
            </FormField>
            <FormField label="Lời giải">
              {(f) => <Textarea {...f} rows={5} value={form.solution ?? ''} onChange={(e) => set({ solution: e.target.value })} />}
            </FormField>

            <ChapterPicker
              options={gradeChapters}
              loading={!tree && !treeError}
              error={treeError}
              selected={form.chapter_ids}
              invalid={touched && form.chapter_ids.length === 0}
              onChange={(chapter_ids) => set({ chapter_ids })}
            />
          </CardContent>
        </Card>

        <Card className="2xl:sticky 2xl:top-6">
          <CardHeader>
            <CardTitle>Xem trước</CardTitle>
          </CardHeader>
          <CardContent className="pt-0">
            <QuestionView type={form.type} content={form.content} statements={form.statements}
              correctAnswer={form.correct_answer} solution={form.solution} />
          </CardContent>
        </Card>
      </div>
    </>
  );
}

function ChapterPicker({ options, loading, error, selected, invalid, onChange }: {
  options: Array<{ node: ChapterNode; depth: number }>;
  loading: boolean;
  error: string | null;
  selected: number[];
  invalid: boolean;
  onChange: (ids: number[]) => void;
}) {
  const [filter, setFilter] = useState('');
  const shown = filter
    ? options.filter(({ node }) => chapterLabel(node).toLowerCase().includes(filter.toLowerCase()))
    : options;
  const toggle = (id: number) => onChange(selected.includes(id) ? selected.filter((x) => x !== id) : [...selected, id]);
  return (
    <fieldset className="grid gap-2">
      <legend className="mb-1 text-label">
        Chương <span className="text-danger" aria-hidden="true">*</span>
        <span className="ml-2 text-caption text-muted-foreground">Đã chọn {selected.length}/10 · cùng một khối</span>
      </legend>
      {error && <Alert tone="danger" title="Không tải được danh mục chương">{error}</Alert>}
      {loading && <Skeleton className="h-40 w-full" />}
      {!loading && !error && (
        <>
          <Input aria-label="Lọc chương" placeholder="Lọc theo mã hoặc tên chương" value={filter} onChange={(e) => setFilter(e.target.value)} />
          <div className={cn('max-h-64 overflow-y-auto rounded-xl border p-2', invalid ? 'border-danger' : 'border-border')}>
            {shown.length === 0 && <p className="p-2 text-label text-muted-foreground">Không có chương phù hợp.</p>}
            {shown.map(({ node, depth }) => (
              <label key={node.chapter_id} className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-label hover:bg-surface-muted"
                style={{ paddingLeft: `${0.5 + depth * 1.25}rem` }}>
                <input type="checkbox" className="size-4 accent-[var(--color-primary)]" checked={selected.includes(node.chapter_id)}
                  onChange={() => toggle(node.chapter_id)} />
                <span className={depth === 0 ? 'font-semibold' : undefined}>{chapterLabel(node)}</span>
              </label>
            ))}
          </div>
        </>
      )}
    </fieldset>
  );
}
