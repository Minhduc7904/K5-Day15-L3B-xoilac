'use client';

/** Trang /admin/questions/[id] (#11): nội dung hiển thị như học sinh thấy, đáp án, lời giải, chương, số đề tham chiếu. */
import { Archive, ArrowLeft, Pencil, RotateCcw } from 'lucide-react';
import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, Badge, Skeleton } from '@/components/ui/feedback';
import { useToast } from '@/components/ui/toast';
import { ConfirmModal, formatTime, PageHeader } from '@/features/admin/admin-ui';
import { chapterLabel } from '@/features/admin-chapters/api';
import { toApiError, type ApiError } from '@/lib/api-error';
import { adminQuestionsApi } from '../api';
import { DIFFICULTIES, QUESTION_TYPES, STATUSES, type QuestionDetail } from '../types';
import { statusTone } from './question-list';
import { QuestionView } from './question-view';

export function QuestionDetailPage({ id }: { id: number }) {
  const toast = useToast();
  const [q, setQ] = useState<QuestionDetail | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setQ(await adminQuestionsApi.get(id));
      setError(null);
    } catch (e) {
      setError(toApiError(e));
    }
  }, [id]);
  useEffect(() => {
    void load();
  }, [load]);

  const toggle = async () => {
    if (!q) return;
    setBusy(true);
    try {
      const next = q.status === 'ARCHIVED' ? await adminQuestionsApi.restore(q.question_id) : await adminQuestionsApi.archive(q.question_id);
      setQ(next);
      toast({ tone: 'success', title: next.status === 'ARCHIVED' ? 'Đã ngừng sử dụng câu hỏi' : 'Đã khôi phục câu hỏi', description: next.code });
      setConfirming(false);
    } catch (e) {
      toast({ tone: 'danger', title: 'Không đổi được trạng thái', description: toApiError(e).message });
    } finally {
      setBusy(false);
    }
  };

  const back = <Button href="/admin/questions" size="sm" variant="ghost" leftIcon={<ArrowLeft aria-hidden="true" />}>Danh sách</Button>;
  if (error)
    return (
      <>
        <PageHeader title="Câu hỏi" actions={back} />
        <Alert tone={error.status === 404 ? 'warning' : 'danger'} title={error.status === 404 ? 'Không có câu hỏi này' : 'Không tải được câu hỏi'}>
          {error.status === 404 ? null : error.message}
        </Alert>
      </>
    );
  if (!q) return <Skeleton className="h-96 w-full" />;

  const archived = q.status === 'ARCHIVED';
  return (
    <>
      <PageHeader
        title={`Câu ${q.code}`}
        description={`Tạo ${formatTime(q.created_at)} · Sửa lần cuối ${formatTime(q.updated_at)}`}
        actions={
          <>
            {back}
            <Button href={`/admin/questions/${q.question_id}/edit`} size="sm" variant="outline" leftIcon={<Pencil aria-hidden="true" />}>Sửa</Button>
            <Button size="sm" variant={archived ? 'primary' : 'danger'} leftIcon={archived ? <RotateCcw aria-hidden="true" /> : <Archive aria-hidden="true" />}
              onClick={() => setConfirming(true)}>
              {archived ? 'Khôi phục' : 'Ngừng sử dụng'}
            </Button>
          </>
        }
      />
      {archived && (
        <Alert tone="warning" title={`Đã ngừng sử dụng từ ${formatTime(q.archived_at)}`} className="mb-4">
          Câu này không còn được chọn cho đề mới. Đề và lịch sử làm bài đã có câu này vẫn đọc được.
        </Alert>
      )}
      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem] xl:items-start">
        <Card>
          <CardContent>
            <QuestionView type={q.type} content={q.content} statements={q.statements} correctAnswer={q.correct_answer} solution={q.solution} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Thông tin</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 pt-0 text-label">
            <Row label="Trạng thái"><Badge tone={statusTone(q.status)} dot>{STATUSES[q.status]}</Badge></Row>
            <Row label="Loại câu">{QUESTION_TYPES[q.type]}</Row>
            <Row label="Khối">{q.grade ? `Lớp ${q.grade}` : '—'}</Row>
            <Row label="Độ khó">{q.difficulty ? `${q.difficulty} · ${DIFFICULTIES[q.difficulty]}` : '—'}</Row>
            <Row label="Chương">
              <div className="flex flex-wrap justify-end gap-1">
                {q.chapters.map((c) => <Badge key={c.chapter_id}>{chapterLabel(c)}</Badge>)}
              </div>
            </Row>
            <Row label="Đề đang dùng">{q.exam_count}</Row>
            <Row label="Ảnh">{q.media_ids.length ? q.media_ids.map((m) => `media:${m}`).join(', ') : '—'}</Row>
          </CardContent>
        </Card>
      </div>
      <ConfirmModal
        open={confirming}
        title={archived ? 'Khôi phục câu hỏi?' : 'Ngừng sử dụng câu hỏi?'}
        description={archived
          ? 'Câu sẽ được chọn lại cho đề mới nếu đang ở trạng thái đã duyệt.'
          : `Câu không còn được chọn cho đề mới. ${q.exam_count} đề đang tham chiếu vẫn giữ nguyên.`}
        confirmLabel={archived ? 'Khôi phục' : 'Ngừng sử dụng'}
        tone={archived ? 'primary' : 'danger'}
        busy={busy}
        onConfirm={() => void toggle()}
        onClose={() => setConfirming(false)}
      />
    </>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <span className="shrink-0 text-muted-foreground">{label}</span>
      <div className="text-right text-foreground">{children}</div>
    </div>
  );
}
