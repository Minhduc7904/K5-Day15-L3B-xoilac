'use client';

/**
 * Trang /admin/chapters (#11): cây chương theo khối 10/11/12, mở/thu gọn, tạo chương con, đổi tên, sửa mã,
 * chuyển sang chương cha khác, xoá. Lỗi từ API (mã trùng, vòng lặp, chương đang dùng) hiện nguyên văn.
 */
import { ChevronDown, ChevronRight, Pencil, Plus, Trash } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Button, IconButton } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Alert, Badge, Skeleton } from '@/components/ui/feedback';
import { FormField } from '@/components/ui/form-field';
import { Input } from '@/components/ui/input';
import { Modal } from '@/components/ui/modal';
import { useToast } from '@/components/ui/toast';
import { ConfirmModal, EmptyState, PageHeader, selectClass } from '@/features/admin/admin-ui';
import { cn } from '@/lib/cn';
import { toApiError, type ApiError } from '@/lib/api-error';
import { adminChaptersApi, chapterLabel, flattenTree, type ChapterInput, type ChapterNode } from '../api';

const GRADES = [10, 11, 12] as const;
const CODE_RE = /^(10|11|12)C[0-9A-Za-z._-]+$/;

type Editing = { mode: 'create'; parent: ChapterNode | null } | { mode: 'edit'; node: ChapterNode };

export function ChapterTreePage() {
  const toast = useToast();
  const [grade, setGrade] = useState<number>(12);
  const [tree, setTree] = useState<ChapterNode[] | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set());
  const [editing, setEditing] = useState<Editing | null>(null);
  const [deleting, setDeleting] = useState<ChapterNode | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      setTree(await adminChaptersApi.tree(grade));
      setError(null);
    } catch (e) {
      setError(toApiError(e));
    }
  }, [grade]);
  useEffect(() => {
    setTree(null);
    void load();
  }, [load]);

  const toggle = (id: number) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const remove = async (node: ChapterNode) => {
    setBusy(true);
    try {
      await adminChaptersApi.remove(node.chapter_id);
      toast({ tone: 'success', title: 'Đã xoá chương', description: chapterLabel(node) });
      setDeleting(null);
      await load();
    } catch (e) {
      toast({ tone: 'danger', title: 'Không xoá được chương', description: toApiError(e).message });
    } finally {
      setBusy(false);
    }
  };

  const allIds = useMemo(() => (tree ? flattenTree(tree).map((x) => x.node.chapter_id) : []), [tree]);

  return (
    <>
      <PageHeader
        title="Danh mục chương"
        description="Cây chương Toán THPT theo khối. Mã chương dạng <khối>C<số>, vd 12C11."
        actions={<Button size="sm" leftIcon={<Plus aria-hidden="true" />} onClick={() => setEditing({ mode: 'create', parent: null })}>Thêm chương gốc</Button>}
      />
      <Card>
        <CardContent className="grid gap-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex gap-1 rounded-xl bg-surface-muted p-1" role="tablist" aria-label="Chọn khối">
              {GRADES.map((g) => (
                <button key={g} type="button" role="tab" aria-selected={grade === g} onClick={() => setGrade(g)}
                  className={cn('rounded-lg px-4 py-1.5 text-label', grade === g ? 'bg-background font-semibold text-foreground shadow-soft' : 'text-muted-foreground hover:text-foreground')}>
                  Lớp {g}
                </button>
              ))}
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="ghost" onClick={() => setCollapsed(new Set())}>Mở hết</Button>
              <Button size="sm" variant="ghost" onClick={() => setCollapsed(new Set(allIds))}>Thu gọn hết</Button>
            </div>
          </div>
          {error && (
            <Alert tone="danger" title="Không tải được cây chương" action={<Button size="sm" variant="outline" onClick={() => void load()}>Thử lại</Button>}>
              {error.message}
            </Alert>
          )}
          {!tree && !error && <Skeleton className="h-64 w-full" />}
          {tree && tree.length === 0 && <EmptyState>Khối {grade} chưa có chương nào.</EmptyState>}
          {tree && tree.length > 0 && (
            <ul role="tree" aria-label={`Chương lớp ${grade}`} className="grid gap-0.5">
              {tree.map((node) => (
                <TreeRow key={node.chapter_id} node={node} depth={0} collapsed={collapsed} onToggle={toggle}
                  onAdd={(parent) => setEditing({ mode: 'create', parent })}
                  onEdit={(n) => setEditing({ mode: 'edit', node: n })}
                  onDelete={setDeleting} />
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      <ChapterFormModal
        editing={editing}
        grade={grade}
        tree={tree ?? []}
        onClose={() => setEditing(null)}
        onSaved={(saved, created) => {
          setEditing(null);
          toast({ tone: 'success', title: created ? 'Đã tạo chương' : 'Đã lưu chương', description: chapterLabel(saved) });
          void load();
        }}
      />
      <ConfirmModal
        open={deleting !== null}
        title="Xoá chương?"
        description={deleting ? `${chapterLabel(deleting)} sẽ bị xoá. Chỉ xoá được chương không còn chương con và không còn câu hỏi.` : undefined}
        confirmLabel="Xoá"
        busy={busy}
        onConfirm={() => deleting && void remove(deleting)}
        onClose={() => setDeleting(null)}
      />
    </>
  );
}

function TreeRow({ node, depth, collapsed, onToggle, onAdd, onEdit, onDelete }: {
  node: ChapterNode; depth: number; collapsed: Set<number>; onToggle: (id: number) => void;
  onAdd: (n: ChapterNode) => void; onEdit: (n: ChapterNode) => void; onDelete: (n: ChapterNode) => void;
}) {
  const open = !collapsed.has(node.chapter_id);
  const hasChildren = node.children.length > 0;
  return (
    <li role="treeitem" aria-expanded={hasChildren ? open : undefined} aria-selected={false}>
      <div className="group flex flex-wrap items-center gap-2 rounded-xl px-2 py-1.5 hover:bg-surface-muted" style={{ paddingLeft: `${0.5 + depth * 1.5}rem` }}>
        {hasChildren ? (
          <IconButton size="sm" label={open ? 'Thu gọn' : 'Mở rộng'} onClick={() => onToggle(node.chapter_id)}>
            {open ? <ChevronDown aria-hidden="true" /> : <ChevronRight aria-hidden="true" />}
          </IconButton>
        ) : (
          <span className="size-9 shrink-0" aria-hidden="true" />
        )}
        <span className="font-mono text-caption text-muted-foreground">{node.code ?? '—'}</span>
        <span className={cn('min-w-0 flex-1 text-label', depth === 0 && 'font-semibold')}>{node.name}</span>
        <Badge tone={node.subtree_question_count ? 'primary' : 'neutral'}>
          {node.question_count} câu{hasChildren ? ` · nhánh ${node.subtree_question_count}` : ''}
        </Badge>
        <div className="flex gap-0.5">
          <IconButton size="sm" label={`Thêm chương con của ${node.code ?? node.name}`} onClick={() => onAdd(node)}><Plus aria-hidden="true" /></IconButton>
          <IconButton size="sm" label={`Sửa ${node.code ?? node.name}`} onClick={() => onEdit(node)}><Pencil aria-hidden="true" /></IconButton>
          <IconButton size="sm" label={`Xoá ${node.code ?? node.name}`} onClick={() => onDelete(node)}><Trash aria-hidden="true" /></IconButton>
        </div>
      </div>
      {hasChildren && open && (
        <ul role="group" className="grid gap-0.5">
          {node.children.map((child) => (
            <TreeRow key={child.chapter_id} node={child} depth={depth + 1} collapsed={collapsed} onToggle={onToggle}
              onAdd={onAdd} onEdit={onEdit} onDelete={onDelete} />
          ))}
        </ul>
      )}
    </li>
  );
}

function ChapterFormModal({ editing, grade, tree, onClose, onSaved }: {
  editing: Editing | null; grade: number; tree: ChapterNode[];
  onClose: () => void; onSaved: (node: ChapterNode, created: boolean) => void;
}) {
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [slug, setSlug] = useState('');
  const [parentId, setParentId] = useState<string>('');
  const [order, setOrder] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [touched, setTouched] = useState(false);

  useEffect(() => {
    if (!editing) return;
    setError(null);
    setTouched(false);
    if (editing.mode === 'edit') {
      const n = editing.node;
      setName(n.name);
      setCode(n.code ?? '');
      setSlug(n.slug ?? '');
      setParentId(n.parent_chapter_id ? String(n.parent_chapter_id) : '');
      setOrder(n.order_in_parent != null ? String(n.order_in_parent) : '');
    } else {
      setName('');
      setCode(editing.parent?.code ? `${editing.parent.code}` : `${grade}C`);
      setSlug('');
      setParentId(editing.parent ? String(editing.parent.chapter_id) : '');
      setOrder('');
    }
  }, [editing, grade]);

  // Chương cha có thể chọn: mọi chương của khối, trừ chính nó (backend vẫn kiểm vòng lặp với cả nhánh con).
  const parents = flattenTree(tree).filter(({ node }) => editing?.mode !== 'edit' || node.chapter_id !== editing.node.chapter_id);
  const codeError = touched && !CODE_RE.test(code.trim()) ? 'Mã dạng <khối>C<số>, vd 12C11.' : undefined;
  const nameError = touched && !name.trim() ? 'Nhập tên chương.' : undefined;

  const submit = async () => {
    setTouched(true);
    if (!editing || !name.trim() || !CODE_RE.test(code.trim())) return;
    const body: ChapterInput = {
      name: name.trim(),
      code: code.trim(),
      slug: slug.trim() || null,
      parent_chapter_id: parentId ? Number(parentId) : null,
      order_in_parent: order.trim() ? Number(order) : null,
    };
    setSaving(true);
    setError(null);
    try {
      const saved = editing.mode === 'edit'
        ? await adminChaptersApi.update(editing.node.chapter_id, body)
        : await adminChaptersApi.create(body);
      onSaved(saved, editing.mode === 'create');
    } catch (e) {
      const err = toApiError(e);
      setError(err.fieldErrors ? Object.values(err.fieldErrors).join(' ') : err.message);
    } finally {
      setSaving(false);
    }
  };

  const title = editing?.mode === 'edit' ? `Sửa ${editing.node.code ?? editing.node.name}`
    : editing?.parent ? `Thêm chương con của ${editing.parent.code ?? editing.parent.name}` : `Thêm chương gốc lớp ${grade}`;

  return (
    <Modal open={editing !== null} onClose={onClose} title={title} className="w-[min(36rem,calc(100vw-2rem))]">
      <form className="grid gap-4" onSubmit={(e) => {
        e.preventDefault();
        void submit();
      }}>
        {error && <Alert tone="danger" title="Không lưu được">{error}</Alert>}
        <FormField label="Tên chương" required error={nameError}>
          {(f) => <Input {...f} value={name} maxLength={191} onChange={(e) => setName(e.target.value)} />}
        </FormField>
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Mã chương" required error={codeError} hint="Không trùng với chương khác.">
            {(f) => <Input {...f} value={code} maxLength={191} onChange={(e) => setCode(e.target.value)} />}
          </FormField>
          <FormField label="Slug" hint="Để trống thì tự sinh từ mã và tên.">
            {(f) => <Input {...f} value={slug} maxLength={191} onChange={(e) => setSlug(e.target.value)} />}
          </FormField>
        </div>
        <div className="grid gap-4 sm:grid-cols-[minmax(0,1fr)_8rem]">
          <FormField label="Chương cha">
            {(f) => (
              <select {...f} className={selectClass} value={parentId} onChange={(e) => setParentId(e.target.value)}>
                <option value="">— Chương gốc —</option>
                {parents.map(({ node, depth }) => (
                  <option key={node.chapter_id} value={node.chapter_id}>{'  '.repeat(depth)}{chapterLabel(node)}</option>
                ))}
              </select>
            )}
          </FormField>
          <FormField label="Thứ tự" hint="Trống: xếp cuối.">
            {(f) => <Input {...f} type="number" min={0} max={10000} value={order} onChange={(e) => setOrder(e.target.value)} />}
          </FormField>
        </div>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" onClick={onClose} disabled={saving}>Huỷ</Button>
          <Button type="submit" loading={saving}>{editing?.mode === 'edit' ? 'Lưu' : 'Tạo chương'}</Button>
        </div>
      </form>
    </Modal>
  );
}
