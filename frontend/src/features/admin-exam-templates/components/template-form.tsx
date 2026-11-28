'use client';

/**
 * Trang /admin/exam-templates/new và /admin/exam-templates/[id] (#11 dựng UI cho API của #5).
 * Sửa thông tin mẫu và từng phần (loại câu, số câu, điểm, phân bố độ khó, chương). Luật liên trường do #5 kiểm;
 * lỗi 422 hiện danh sách lý do từ backend.
 */
import { ArrowLeft, BadgeCheck, Plus, Save, Trash } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Button, IconButton } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, Badge, Skeleton } from '@/components/ui/feedback';
import { FormField } from '@/components/ui/form-field';
import { Input, Textarea } from '@/components/ui/input';
import { useToast } from '@/components/ui/toast';
import { PageHeader, selectClass } from '@/features/admin/admin-ui';
import { QUESTION_TYPES } from '@/features/admin-questions/types';
import { toApiError } from '@/lib/api-error';
import {
  EXAM_TYPES, examTemplatesApi,
  type Difficulty, type ExamTemplate, type ExamTemplateInput, type ExamType, type SectionType, type TemplateSection,
} from '../api';

const DIFFS: Difficulty[] = ['NB', 'TH', 'VD', 'VDC'];

interface SectionForm {
  title: string;
  question_type: SectionType;
  count: string;
  points: string;
  dist: Record<Difficulty, string>;
  chapters: string;
}

interface Form {
  name: string;
  exam_type: ExamType;
  grade: string;
  version_label: string;
  duration_minutes: string;
  source: string;
  description: string;
  sections: SectionForm[];
}

const emptySection = (): SectionForm => ({
  title: '', question_type: 'SINGLE_CHOICE', count: '10', points: '', dist: { NB: '', TH: '', VD: '', VDC: '' }, chapters: '',
});

const toForm = (t?: ExamTemplate): Form => t ? {
  name: t.name,
  exam_type: t.exam_type,
  grade: t.grade ? String(t.grade) : '',
  version_label: t.version_label ?? '',
  duration_minutes: t.duration_minutes ? String(t.duration_minutes) : '',
  source: t.source ?? '',
  description: t.description ?? '',
  sections: t.sections.map((s) => ({
    title: s.title,
    question_type: s.question_type,
    count: String(s.count),
    points: s.points_per_question != null ? String(s.points_per_question) : '',
    dist: Object.fromEntries(DIFFS.map((d) => [d, s.difficulty_distribution?.[d] != null ? String(s.difficulty_distribution[d]) : ''])) as Record<Difficulty, string>,
    chapters: (s.chapter_codes ?? []).join(', '),
  })),
} : {
  name: '', exam_type: 'THPT', grade: '12', version_label: '', duration_minutes: '90', source: '', description: '', sections: [emptySection()],
};

const num = (v: string) => (v.trim() === '' ? null : Number(v));

function toInput(f: Form): ExamTemplateInput {
  return {
    name: f.name.trim(),
    exam_type: f.exam_type,
    grade: num(f.grade),
    version_label: f.version_label.trim() || null,
    duration_minutes: num(f.duration_minutes),
    source: f.source.trim() || null,
    description: f.description.trim() || null,
    sections: f.sections.map((s, i): TemplateSection => {
      const dist = Object.fromEntries(DIFFS.filter((d) => s.dist[d].trim() !== '').map((d) => [d, Number(s.dist[d])]));
      const chapters = s.chapters.split(/[,\s]+/).map((c) => c.trim()).filter(Boolean);
      return {
        order: i + 1,
        title: s.title.trim(),
        question_type: s.question_type,
        count: Number(s.count),
        points_per_question: num(s.points),
        difficulty_distribution: Object.keys(dist).length ? dist : null,
        chapter_codes: chapters.length ? chapters : null,
      };
    }),
  };
}

/** Kiểm hình dạng tối thiểu trước khi gửi; luật nghiệp vụ để backend #5 quyết định. */
function check(f: Form): string | null {
  if (!f.name.trim()) return 'Nhập tên mẫu';
  if (!f.sections.length) return 'Mẫu cần ít nhất một phần';
  for (const [i, s] of f.sections.entries()) {
    if (!s.title.trim()) return `Phần ${i + 1}: nhập tiêu đề`;
    const count = Number(s.count);
    if (!Number.isInteger(count) || count < 1 || count > 100) return `Phần ${i + 1}: số câu từ 1 đến 100`;
    const filled = DIFFS.filter((d) => s.dist[d].trim() !== '');
    if (filled.length && filled.reduce((sum, d) => sum + Number(s.dist[d]), 0) !== count)
      return `Phần ${i + 1}: tổng phân bố độ khó phải bằng số câu (${count})`;
  }
  return null;
}

export function TemplateFormPage({ id }: { id?: number }) {
  const router = useRouter();
  const toast = useToast();
  const [template, setTemplate] = useState<ExamTemplate | null>(null);
  const [form, setForm] = useState<Form | null>(id ? null : toForm());
  const [loadError, setLoadError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [touched, setTouched] = useState(false);
  const [busy, setBusy] = useState<'save' | 'approve' | null>(null);

  useEffect(() => {
    if (!id) return;
    let cancelled = false;
    examTemplatesApi.get(id)
      .then((t) => {
        if (cancelled) return;
        setTemplate(t);
        setForm(toForm(t));
      })
      .catch((e) => !cancelled && setLoadError(toApiError(e).message));
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loadError) return <Alert tone="danger" title="Không tải được mẫu">{loadError}</Alert>;
  if (!form) return <Skeleton className="h-96 w-full" />;

  const problem = check(form);
  const set = (changes: Partial<Form>) => setForm((f) => (f ? { ...f, ...changes } : f));
  const setSection = (i: number, changes: Partial<SectionForm>) =>
    set({ sections: form.sections.map((s, j) => (j === i ? { ...s, ...changes } : s)) });
  const total = form.sections.reduce((sum, s) => sum + (Number(s.count) || 0), 0);

  const save = async (andApprove = false) => {
    setTouched(true);
    if (problem) return;
    setBusy(andApprove ? 'approve' : 'save');
    setError(null);
    try {
      let saved = id ? await examTemplatesApi.update(id, toInput(form)) : await examTemplatesApi.create(toInput(form));
      if (andApprove) saved = await examTemplatesApi.approve(saved.template_id);
      toast({ tone: 'success', title: andApprove ? 'Đã lưu và duyệt mẫu' : id ? 'Đã lưu mẫu' : 'Đã tạo mẫu', description: saved.name });
      setTemplate(saved);
      setForm(toForm(saved));
      if (!id) router.replace(`/admin/exam-templates/${saved.template_id}`);
    } catch (e) {
      setError(toApiError(e).message);
    } finally {
      setBusy(null);
    }
  };

  return (
    <>
      <PageHeader
        title={id ? `Sửa mẫu${template ? `: ${template.name}` : ''}` : 'Thêm mẫu cấu trúc đề'}
        actions={
          <>
            <Button href="/admin/exam-templates" size="sm" variant="ghost" leftIcon={<ArrowLeft aria-hidden="true" />}>Danh sách</Button>
            <Button size="sm" variant="outline" loading={busy === 'save'} disabled={busy !== null} leftIcon={<Save aria-hidden="true" />} onClick={() => void save()}>Lưu</Button>
            {template?.status !== 'APPROVED' && (
              <Button size="sm" loading={busy === 'approve'} disabled={busy !== null} leftIcon={<BadgeCheck aria-hidden="true" />} onClick={() => void save(true)}>Lưu và duyệt</Button>
            )}
          </>
        }
      />
      {template && (
        <div className="mb-4 flex gap-2">
          <Badge tone={template.status === 'APPROVED' ? 'success' : 'warning'} dot>{template.status === 'APPROVED' ? 'Đã duyệt' : 'Nháp'}</Badge>
          <Badge>{template.total_questions} câu</Badge>
        </div>
      )}
      {touched && problem && <Alert tone="warning" title={problem} className="mb-4" />}
      {error && <Alert tone="danger" title="Không lưu được mẫu" className="mb-4">{error}</Alert>}
      <div className="grid gap-6">
        <Card>
          <CardContent className="grid gap-4">
            <div className="grid gap-4 md:grid-cols-2">
              <FormField label="Tên mẫu" required>
                {(f) => <Input {...f} value={form.name} maxLength={255} onChange={(e) => set({ name: e.target.value })} />}
              </FormField>
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField label="Kỳ thi" required>
                  {(f) => (
                    <select {...f} className={selectClass} value={form.exam_type} onChange={(e) => set({ exam_type: e.target.value as ExamType })}>
                      {Object.entries(EXAM_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                    </select>
                  )}
                </FormField>
                <FormField label="Khối" hint="Bắt buộc với giữa kỳ, cuối kỳ.">
                  {(f) => (
                    <select {...f} className={selectClass} value={form.grade} onChange={(e) => set({ grade: e.target.value })}>
                      <option value="">Không ghi khối</option>
                      {[10, 11, 12].map((g) => <option key={g} value={g}>Lớp {g}</option>)}
                    </select>
                  )}
                </FormField>
              </div>
              <div className="grid gap-4 sm:grid-cols-2">
                <FormField label="Năm / phiên bản">
                  {(f) => <Input {...f} value={form.version_label} maxLength={50} onChange={(e) => set({ version_label: e.target.value })} />}
                </FormField>
                <FormField label="Thời gian (phút)">
                  {(f) => <Input {...f} type="number" min={1} max={300} value={form.duration_minutes} onChange={(e) => set({ duration_minutes: e.target.value })} />}
                </FormField>
              </div>
              <FormField label="Nguồn căn cứ" hint="Bắt buộc khi duyệt: văn bản, đề minh hoạ hoặc ma trận.">
                {(f) => <Input {...f} value={form.source} maxLength={2000} onChange={(e) => set({ source: e.target.value })} />}
              </FormField>
            </div>
            <FormField label="Mô tả">
              {(f) => <Textarea {...f} rows={2} value={form.description} maxLength={5000} onChange={(e) => set({ description: e.target.value })} />}
            </FormField>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2">
            <CardTitle>Các phần ({total} câu)</CardTitle>
            <Button size="sm" variant="ghost" leftIcon={<Plus aria-hidden="true" />} disabled={form.sections.length >= 20}
              onClick={() => set({ sections: [...form.sections, emptySection()] })}>
              Thêm phần
            </Button>
          </CardHeader>
          <CardContent className="grid gap-4 pt-0">
            {form.sections.map((s, i) => (
              <div key={i} className="grid gap-3 rounded-2xl border border-border p-4">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-label font-semibold">Phần {i + 1}</span>
                  <IconButton size="sm" label={`Xoá phần ${i + 1}`} disabled={form.sections.length <= 1}
                    onClick={() => set({ sections: form.sections.filter((_, j) => j !== i) })}>
                    <Trash aria-hidden="true" />
                  </IconButton>
                </div>
                <div className="grid gap-3 md:grid-cols-[minmax(0,2fr)_minmax(0,1.5fr)_6rem_6rem]">
                  <FormField label="Tiêu đề" required>
                    {(f) => <Input {...f} value={s.title} maxLength={255} onChange={(e) => setSection(i, { title: e.target.value })} />}
                  </FormField>
                  <FormField label="Loại câu">
                    {(f) => (
                      <select {...f} className={selectClass} value={s.question_type} onChange={(e) => setSection(i, { question_type: e.target.value as SectionType })}>
                        {Object.entries(QUESTION_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
                      </select>
                    )}
                  </FormField>
                  <FormField label="Số câu" required>
                    {(f) => <Input {...f} type="number" min={1} max={100} value={s.count} onChange={(e) => setSection(i, { count: e.target.value })} />}
                  </FormField>
                  <FormField label="Điểm/câu">
                    {(f) => <Input {...f} type="number" min={0} max={10} step="0.05" value={s.points} onChange={(e) => setSection(i, { points: e.target.value })} />}
                  </FormField>
                </div>
                <div className="grid gap-3 md:grid-cols-[repeat(4,6rem)_minmax(0,1fr)]">
                  {DIFFS.map((d) => (
                    <FormField key={d} label={d}>
                      {(f) => <Input {...f} type="number" min={0} max={100} value={s.dist[d]}
                        onChange={(e) => setSection(i, { dist: { ...s.dist, [d]: e.target.value } })} />}
                    </FormField>
                  ))}
                  <FormField label="Mã chương" hint="Cách nhau bởi dấu phẩy; để trống là mọi chương.">
                    {(f) => <Input {...f} value={s.chapters} onChange={(e) => setSection(i, { chapters: e.target.value })} />}
                  </FormField>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </>
  );
}
