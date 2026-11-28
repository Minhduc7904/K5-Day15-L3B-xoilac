'use client';

/**
 * Trang /admin/questions (#11): tìm, lọc theo khối, chương (gồm chương con), loại, độ khó, trạng thái; phân trang.
 * Bộ lọc nằm trên URL (?q=&grade=&chapter=&type=&difficulty=&status=&page=) nên tải lại trang vẫn giữ.
 */
import { Archive, Eye, Pencil, Plus, RotateCcw, Search } from 'lucide-react';
import { usePathname, useRouter, useSearchParams } from 'next/navigation';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, Badge, Skeleton } from '@/components/ui/feedback';
import { Input } from '@/components/ui/input';
import { useToast } from '@/components/ui/toast';
import { ConfirmModal, EmptyState, PageHeader, Pagination, selectClass } from '@/features/admin/admin-ui';
import { adminChaptersApi, chapterLabel, flattenTree, type ChapterNode } from '@/features/admin-chapters/api';
import { toApiError, type ApiError } from '@/lib/api-error';
import { adminQuestionsApi } from '../api';
import {
  DIFFICULTIES, GRADES, QUESTION_TYPES, STATUSES,
  type Difficulty, type QuestionList as QuestionPage, type QuestionStatus, type QuestionSummary, type QuestionType,
} from '../types';
import { AdminQuestionContent } from './question-view';

const PAGE_SIZE = 20;

export const statusTone = (s: QuestionStatus) =>
  s === 'PUBLISHED' ? 'success' : s === 'ARCHIVED' ? 'danger' : s === 'DRAFT' ? 'warning' : 'neutral';

function useDebounced<T>(value: T, ms = 350): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = window.setTimeout(() => setDebounced(value), ms);
    return () => window.clearTimeout(t);
  }, [value, ms]);
  return debounced;
}

export function QuestionListPage() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const toast = useToast();

  const filters = useMemo(() => ({
    q: params.get('q') ?? '',
    grade: params.get('grade') ?? '',
    chapter: params.get('chapter') ?? '',
    type: params.get('type') ?? '',
    difficulty: params.get('difficulty') ?? '',
    status: params.get('status') ?? '',
    page: Math.max(1, Number(params.get('page')) || 1),
  }), [params]);

  const setParams = useCallback((changes: Record<string, string | number | null>, resetPage = true) => {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(changes)) {
      if (value === null || value === '') next.delete(key);
      else next.set(key, String(value));
    }
    if (resetPage && !('page' in changes)) next.delete('page');
    const qs = next.toString();
    router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }, [params, pathname, router]);

  const [search, setSearch] = useState(filters.q);
  const debounced = useDebounced(search);
  // Chỉ phụ thuộc `debounced`: đẩy ô tìm lên URL khi người dùng gõ. Thêm filters.q/setParams sẽ đẩy lại chữ cũ
  // ngay sau khi bấm "Xoá bộ lọc" (ô tìm chưa kịp hết thời gian chờ).
  const pushSearch = useRef(setParams);
  pushSearch.current = setParams;
  const currentQ = useRef(filters.q);
  currentQ.current = filters.q;
  useEffect(() => {
    if (debounced.trim() !== currentQ.current) pushSearch.current({ q: debounced.trim() });
  }, [debounced]);

  const [tree, setTree] = useState<ChapterNode[] | null>(null);
  useEffect(() => {
    let cancelled = false;
    adminChaptersApi.tree(filters.grade ? Number(filters.grade) : undefined)
      .then((t) => !cancelled && setTree(t))
      .catch(() => !cancelled && setTree([]));
    return () => {
      cancelled = true;
    };
  }, [filters.grade]);

  const [data, setData] = useState<QuestionPage | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(false);
  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await adminQuestionsApi.list({
        q: filters.q || undefined,
        grade: filters.grade ? Number(filters.grade) : undefined,
        chapter_id: filters.chapter ? Number(filters.chapter) : undefined,
        type: (filters.type || undefined) as QuestionType | undefined,
        difficulty: (filters.difficulty || undefined) as Difficulty | undefined,
        status: (filters.status || undefined) as QuestionStatus | undefined,
        page: filters.page,
        page_size: PAGE_SIZE,
      }));
      setError(null);
    } catch (e) {
      setError(toApiError(e));
    } finally {
      setLoading(false);
    }
  }, [filters]);
  useEffect(() => {
    void load();
  }, [load]);

  const [target, setTarget] = useState<QuestionSummary | null>(null);
  const [busy, setBusy] = useState(false);
  const toggleArchive = async (q: QuestionSummary) => {
    setBusy(true);
    try {
      if (q.status === 'ARCHIVED') await adminQuestionsApi.restore(q.question_id);
      else await adminQuestionsApi.archive(q.question_id);
      toast({
        tone: 'success',
        title: q.status === 'ARCHIVED' ? 'Đã khôi phục câu hỏi' : 'Đã ngừng sử dụng câu hỏi',
        description: `${q.code}${q.status === 'ARCHIVED' ? '' : ' không còn được chọn cho đề mới.'}`,
      });
      setTarget(null);
      await load();
    } catch (e) {
      toast({ tone: 'danger', title: 'Không đổi được trạng thái', description: toApiError(e).message });
    } finally {
      setBusy(false);
    }
  };

  const chapterOptions = useMemo(() => (tree ? flattenTree(tree) : []), [tree]);
  const hasFilter = Boolean(filters.q || filters.grade || filters.chapter || filters.type || filters.difficulty || filters.status);

  return (
    <>
      <PageHeader
        title="Ngân hàng câu hỏi"
        description="Chỉ câu “Đã duyệt” và chưa ngừng sử dụng mới được chọn khi dựng đề mới."
        actions={<Button href="/admin/questions/new" size="sm" leftIcon={<Plus aria-hidden="true" />}>Thêm câu hỏi</Button>}
      />
      <Card>
        <CardContent className="grid gap-4 pt-6">
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-[minmax(14rem,1.5fr)_repeat(5,minmax(0,1fr))]">
            <Input
              aria-label="Tìm theo nội dung hoặc mã câu"
              placeholder="Tìm nội dung hoặc mã (Q00012)"
              leftIcon={<Search aria-hidden="true" />}
              value={search}
              maxLength={200}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select aria-label="Lọc khối" className={selectClass} value={filters.grade}
              onChange={(e) => setParams({ grade: e.target.value, chapter: null })}>
              <option value="">Mọi khối</option>
              {GRADES.map((g) => <option key={g} value={g}>Lớp {g}</option>)}
            </select>
            <select aria-label="Lọc chương" className={selectClass} value={filters.chapter}
              onChange={(e) => setParams({ chapter: e.target.value })}>
              <option value="">Mọi chương</option>
              {chapterOptions.map(({ node, depth }) => (
                <option key={node.chapter_id} value={node.chapter_id}>
                  {'  '.repeat(depth)}{chapterLabel(node)}
                </option>
              ))}
            </select>
            <select aria-label="Lọc loại câu" className={selectClass} value={filters.type} onChange={(e) => setParams({ type: e.target.value })}>
              <option value="">Mọi loại câu</option>
              {Object.entries(QUESTION_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select aria-label="Lọc độ khó" className={selectClass} value={filters.difficulty}
              onChange={(e) => setParams({ difficulty: e.target.value })}>
              <option value="">Mọi độ khó</option>
              {Object.entries(DIFFICULTIES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
            <select aria-label="Lọc trạng thái" className={selectClass} value={filters.status} onChange={(e) => setParams({ status: e.target.value })}>
              <option value="">Mọi trạng thái</option>
              {Object.entries(STATUSES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </select>
          </div>
          {hasFilter && (
            <div>
              <Button size="sm" variant="ghost" onClick={() => {
                setSearch('');
                router.replace(pathname, { scroll: false });
              }}>
                Xoá bộ lọc
              </Button>
            </div>
          )}

          {error && (
            <Alert tone="danger" title="Không tải được danh sách câu hỏi" action={<Button size="sm" variant="outline" onClick={() => void load()}>Thử lại</Button>}>
              {error.message}
            </Alert>
          )}
          {!data && !error && <Skeleton className="h-64 w-full" />}
          {data && data.items.length === 0 && (
            <EmptyState>{hasFilter ? 'Không có câu hỏi nào khớp bộ lọc.' : 'Ngân hàng chưa có câu hỏi nào.'}</EmptyState>
          )}
          {data && data.items.length > 0 && (
            <div className={loading ? 'overflow-x-auto opacity-60 transition-opacity' : 'overflow-x-auto'} aria-busy={loading}>
              <table className="w-full min-w-[56rem] text-left text-label">
                <thead className="text-caption text-muted-foreground">
                  <tr className="border-b border-border">
                    <th className="py-2 pr-3 font-medium">Mã</th>
                    <th className="py-2 pr-3 font-medium">Nội dung</th>
                    <th className="py-2 pr-3 font-medium">Loại · Khối · Độ khó</th>
                    <th className="py-2 pr-3 font-medium">Chương</th>
                    <th className="py-2 pr-3 font-medium">Trạng thái</th>
                    <th className="py-2 text-right font-medium">Thao tác</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((q) => (
                    <tr key={q.question_id} className="border-b border-border/60 align-top">
                      <td className="py-2.5 pr-3 font-mono text-caption">{q.code}</td>
                      <td className="max-w-[28rem] py-2.5 pr-3">
                        <div className="line-clamp-2 text-foreground">
                          <AdminQuestionContent source={q.content} inline />
                        </div>
                      </td>
                      <td className="py-2.5 pr-3 text-muted-foreground">
                        <p>{QUESTION_TYPES[q.type]}</p>
                        <p>{q.grade ? `Lớp ${q.grade}` : '—'} · {q.difficulty ?? '—'}</p>
                      </td>
                      <td className="py-2.5 pr-3">
                        <div className="flex flex-wrap gap-1">
                          {q.chapters.map((c) => <Badge key={c.chapter_id} tone="neutral">{c.code ?? c.name}</Badge>)}
                        </div>
                      </td>
                      <td className="py-2.5 pr-3">
                        <Badge tone={statusTone(q.status)} dot>{STATUSES[q.status]}</Badge>
                      </td>
                      <td className="py-2.5">
                        <div className="flex justify-end gap-1">
                          <Button size="sm" variant="ghost" href={`/admin/questions/${q.question_id}`} leftIcon={<Eye aria-hidden="true" />}>Xem</Button>
                          <Button size="sm" variant="ghost" href={`/admin/questions/${q.question_id}/edit`} leftIcon={<Pencil aria-hidden="true" />}>Sửa</Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            disabled={busy}
                            leftIcon={q.status === 'ARCHIVED' ? <RotateCcw aria-hidden="true" /> : <Archive aria-hidden="true" />}
                            onClick={() => setTarget(q)}
                          >
                            {q.status === 'ARCHIVED' ? 'Khôi phục' : 'Ngừng dùng'}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
          {data && data.total > PAGE_SIZE && (
            <Pagination page={filters.page} pageSize={PAGE_SIZE} total={data.total} unit="câu" onPage={(p) => setParams({ page: p }, false)} />
          )}
        </CardContent>
      </Card>

      <ConfirmModal
        open={target !== null}
        title={target?.status === 'ARCHIVED' ? 'Khôi phục câu hỏi?' : 'Ngừng sử dụng câu hỏi?'}
        description={target ? (target.status === 'ARCHIVED'
          ? `${target.code} sẽ được chọn lại cho đề mới nếu đang ở trạng thái đã duyệt.`
          : `${target.code} không còn được chọn cho đề mới. Đề và lịch sử làm bài đã có câu này vẫn giữ nguyên.`) : undefined}
        confirmLabel={target?.status === 'ARCHIVED' ? 'Khôi phục' : 'Ngừng sử dụng'}
        tone={target?.status === 'ARCHIVED' ? 'primary' : 'danger'}
        busy={busy}
        onConfirm={() => target && void toggleArchive(target)}
        onClose={() => setTarget(null)}
      />
    </>
  );
}
