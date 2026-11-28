'use client';

/** Trang /admin/pdf-imports (#11 dựng UI cho API của #3): tải PDF lên, theo dõi trạng thái, mở trang duyệt. */
import { Eye, Upload } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, Badge, Skeleton } from '@/components/ui/feedback';
import { useToast } from '@/components/ui/toast';
import { EmptyState, formatTime, PageHeader } from '@/features/admin/admin-ui';
import { toApiError, type ApiError } from '@/lib/api-error';
import { IMPORT_STATUS, pdfImportsApi, type PdfImport } from '../api';

const PAGE_SIZE = 20;
const POLL_MS = 5000;

export function ImportListPage() {
  const toast = useToast();
  const [page, setPage] = useState(1);
  const [rows, setRows] = useState<PdfImport[] | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      setRows(await pdfImportsApi.list((page - 1) * PAGE_SIZE, PAGE_SIZE + 1));
      setError(null);
    } catch (e) {
      setError(toApiError(e));
    }
  }, [page]);
  useEffect(() => {
    void load();
  }, [load]);

  const running = rows?.some((r) => r.status === 'queued' || r.status === 'processing');
  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(() => document.visibilityState === 'visible' && void load(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [running, load]);

  const upload = async (file: File) => {
    setUploading(true);
    try {
      const row = await pdfImportsApi.upload(file);
      toast({ tone: 'success', title: 'Đã nhận PDF', description: `${row.filename}: đang xử lý OCR và tách câu.` });
      setPage(1);
      await load();
    } catch (e) {
      toast({ tone: 'danger', title: 'Không tải được PDF', description: toApiError(e).message });
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = '';
    }
  };

  const shown = rows?.slice(0, PAGE_SIZE) ?? [];
  const hasNext = (rows?.length ?? 0) > PAGE_SIZE;

  return (
    <>
      <PageHeader
        title="Nhập đề PDF"
        description="Tải đề PDF tối đa 60 trang và 20 MiB. Hệ thống OCR và tách câu thành bản nháp để admin duyệt."
        actions={
          <>
            <input ref={fileRef} type="file" accept="application/pdf" className="sr-only" aria-label="Chọn tệp PDF"
              onChange={(e) => e.target.files?.[0] && void upload(e.target.files[0])} />
            <Button size="sm" loading={uploading} leftIcon={<Upload aria-hidden="true" />} onClick={() => fileRef.current?.click()}>
              Tải PDF lên
            </Button>
          </>
        }
      />
      <Card>
        <CardContent className="grid gap-4">
          {error && (
            <Alert tone="danger" title="Không tải được danh sách" action={<Button size="sm" variant="outline" onClick={() => void load()}>Thử lại</Button>}>
              {error.message}
            </Alert>
          )}
          {!rows && !error && <Skeleton className="h-48 w-full" />}
          {rows && shown.length === 0 && <EmptyState>Chưa có phiên nhập PDF nào.</EmptyState>}
          {shown.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[44rem] text-left text-label">
                <thead className="text-caption text-muted-foreground">
                  <tr className="border-b border-border">
                    <th className="py-2 pr-3 font-medium">Tệp</th>
                    <th className="py-2 pr-3 font-medium">Trạng thái</th>
                    <th className="py-2 pr-3 font-medium">Số trang</th>
                    <th className="py-2 pr-3 font-medium">Tạo lúc</th>
                    <th className="py-2 text-right font-medium">Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {shown.map((r) => (
                    <tr key={r.id} className="border-b border-border/60 align-top">
                      <td className="py-2.5 pr-3">
                        <p className="font-medium text-foreground">{r.filename}</p>
                        {r.error && <p className="text-caption text-danger">{r.error}</p>}
                      </td>
                      <td className="py-2.5 pr-3">
                        <Badge tone={IMPORT_STATUS[r.status]?.tone ?? 'neutral'} dot>{IMPORT_STATUS[r.status]?.label ?? r.status}</Badge>
                        <p className="mt-1 text-caption text-muted-foreground">Bước: {r.stage}</p>
                      </td>
                      <td className="py-2.5 pr-3">{r.pageCount ?? '—'}</td>
                      <td className="py-2.5 pr-3 text-muted-foreground">{formatTime(r.createdAt)}</td>
                      <td className="py-2.5 text-right">
                        <Button size="sm" variant="ghost" href={`/admin/pdf-imports/${r.id}`} leftIcon={<Eye aria-hidden="true" />}>
                          {r.status === 'ready_for_review' ? 'Duyệt' : 'Xem'}
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {(page > 1 || hasNext) && (
            <div className="flex items-center justify-between text-label">
              <span className="text-muted-foreground">Trang {page}</span>
              <div className="flex gap-2">
                <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Trước</Button>
                <Button size="sm" variant="outline" disabled={!hasNext} onClick={() => setPage((p) => p + 1)}>Sau</Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </>
  );
}
