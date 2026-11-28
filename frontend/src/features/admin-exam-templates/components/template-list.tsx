'use client';

/** Trang /admin/exam-templates (#11 dựng UI cho API của #5): lọc, xem, duyệt mẫu cấu trúc đề. */
import { BadgeCheck, Pencil, Plus } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, Badge, Skeleton } from '@/components/ui/feedback';
import { useToast } from '@/components/ui/toast';
import { ConfirmModal, EmptyState, formatTime, PageHeader, selectClass } from '@/features/admin/admin-ui';
import { toApiError, type ApiError } from '@/lib/api-error';
import { EXAM_TYPES, examTemplatesApi, type ExamTemplate, type ExamType, type TemplateStatus } from '../api';

export function TemplateListPage() {
  const toast = useToast();
  const [status, setStatus] = useState<TemplateStatus | ''>('');
  const [examType, setExamType] = useState<ExamType | ''>('');
  const [grade, setGrade] = useState('');
  const [rows, setRows] = useState<ExamTemplate[] | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [approving, setApproving] = useState<ExamTemplate | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setRows(await examTemplatesApi.list({ status: status || undefined, exam_type: examType || undefined, grade: grade ? Number(grade) : undefined }));
      setError(null);
    } catch (e) {
      setError(toApiError(e));
    }
  }, [status, examType, grade]);
  useEffect(() => {
    void load();
  }, [load]);

  const approve = async (t: ExamTemplate) => {
    setBusy(true);
    try {
      await examTemplatesApi.approve(t.template_id);
      toast({ tone: 'success', title: 'Đã duyệt mẫu', description: `${t.name} dùng được cho học sinh tạo đề theo kỳ thi.` });
      setApproving(null);
      await load();
    } catch (e) {
      toast({ tone: 'danger', title: 'Không duyệt được mẫu', description: toApiError(e).message });
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <PageHeader
        title="Mẫu cấu trúc đề"
        description="Chỉ mẫu đã duyệt được pipeline học sinh dùng để dựng đề theo kỳ thi."
        actions={<Button href="/admin/exam-templates/new" size="sm" leftIcon={<Plus aria-hidden="true" />}>Thêm mẫu</Button>}
      />
      <Card>
        <CardContent className="grid gap-4">
          <div className="grid gap-3 sm:grid-cols-3">
            <select aria-label="Lọc trạng thái" className={selectClass} value={status} onChange={(e) => setStatus(e.target.value as TemplateStatus | '')}>
              <option value="">Mọi trạng thái</option>
              <option value="DRAFT">Nháp</option>
              <option value="APPROVED">Đã duyệt</option>
            </select>
            <select aria-label="Lọc loại kỳ thi" className={selectClass} value={examType} onChange={(e) => setExamType(e.target.value as ExamType | '')}>
              <option value="">Mọi kỳ thi</option>
              {Object.entries(EXAM_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select aria-label="Lọc khối" className={selectClass} value={grade} onChange={(e) => setGrade(e.target.value)}>
              <option value="">Mọi khối</option>
              {[10, 11, 12].map((g) => <option key={g} value={g}>Lớp {g}</option>)}
            </select>
          </div>
          {error && (
            <Alert tone="danger" title="Không tải được danh sách mẫu" action={<Button size="sm" variant="outline" onClick={() => void load()}>Thử lại</Button>}>
              {error.message}
            </Alert>
          )}
          {!rows && !error && <Skeleton className="h-48 w-full" />}
          {rows && rows.length === 0 && <EmptyState>Không có mẫu nào khớp bộ lọc.</EmptyState>}
          {rows && rows.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[48rem] text-left text-label">
                <thead className="text-caption text-muted-foreground">
                  <tr className="border-b border-border">
                    <th className="py-2 pr-3 font-medium">Tên mẫu</th>
                    <th className="py-2 pr-3 font-medium">Kỳ thi · Khối</th>
                    <th className="py-2 pr-3 font-medium">Số câu</th>
                    <th className="py-2 pr-3 font-medium">Trạng thái</th>
                    <th className="py-2 pr-3 font-medium">Cập nhật</th>
                    <th className="py-2 text-right font-medium">Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((t) => (
                    <tr key={t.template_id} className="border-b border-border/60 align-top">
                      <td className="py-2.5 pr-3">
                        <p className="font-medium text-foreground">{t.name}</p>
                        <p className="text-caption text-muted-foreground">{t.sections.length} phần{t.version_label ? ` · ${t.version_label}` : ''}{t.duration_minutes ? ` · ${t.duration_minutes} phút` : ''}</p>
                      </td>
                      <td className="py-2.5 pr-3">{EXAM_TYPES[t.exam_type]} · {t.grade ? `Lớp ${t.grade}` : 'mọi khối'}</td>
                      <td className="py-2.5 pr-3 tabular-nums">{t.total_questions}</td>
                      <td className="py-2.5 pr-3">
                        <Badge tone={t.status === 'APPROVED' ? 'success' : 'warning'} dot>{t.status === 'APPROVED' ? 'Đã duyệt' : 'Nháp'}</Badge>
                      </td>
                      <td className="py-2.5 pr-3 text-muted-foreground">{formatTime(t.updated_at)}</td>
                      <td className="py-2.5">
                        <div className="flex justify-end gap-1">
                          <Button size="sm" variant="ghost" href={`/admin/exam-templates/${t.template_id}`} leftIcon={<Pencil aria-hidden="true" />}>Sửa</Button>
                          {t.status === 'DRAFT' && (
                            <Button size="sm" variant="ghost" disabled={busy} leftIcon={<BadgeCheck aria-hidden="true" />} onClick={() => setApproving(t)}>Duyệt</Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
      <ConfirmModal
        open={approving !== null}
        title="Duyệt mẫu cấu trúc đề?"
        description={approving ? `${approving.name} sẽ được học sinh dùng để tạo đề theo kỳ thi. Mẫu cần có nguồn căn cứ.` : undefined}
        confirmLabel="Duyệt"
        tone="primary"
        busy={busy}
        onConfirm={() => approving && void approve(approving)}
        onClose={() => setApproving(null)}
      />
    </>
  );
}
