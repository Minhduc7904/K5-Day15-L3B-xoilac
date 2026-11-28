'use client';

/**
 * Trang /admin (#11): ô học sinh online (#20) và số liệu nhanh của ngân hàng câu hỏi, lối tắt tới các trang quản trị.
 * Chỉ gọi API đã có: /admin/questions (page_size=1 để lấy total), /admin/stats/online-students.
 */
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/feedback';
import { OnlineStudentsCard } from '@/features/admin-stats/online-students-card';
import { adminQuestionsApi } from '@/features/admin-questions/api';
import type { QuestionStatus } from '@/features/admin-questions/types';
import { ADMIN_LINKS } from './admin-shell';
import { PageHeader } from './admin-ui';

const COUNTS: Array<{ label: string; status?: QuestionStatus }> = [
  { label: 'Tổng số câu' },
  { label: 'Đã duyệt, dùng được', status: 'PUBLISHED' },
  { label: 'Nháp', status: 'DRAFT' },
  { label: 'Ngừng sử dụng', status: 'ARCHIVED' },
];

export function AdminDashboard() {
  const [counts, setCounts] = useState<Array<number | null> | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all(
      COUNTS.map((c) => adminQuestionsApi.list({ status: c.status, page: 1, page_size: 1 }).then((r) => r.total).catch(() => null)),
    ).then((values) => !cancelled && setCounts(values));
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <>
      <PageHeader title="Tổng quan" description="Tình hình học sinh online và ngân hàng câu hỏi." />
      <div className="grid gap-6 lg:grid-cols-[20rem_minmax(0,1fr)] lg:items-start">
        <OnlineStudentsCard />
        <div className="grid gap-6">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {COUNTS.map((c, i) => (
              <Link key={c.label} href={c.status ? `/admin/questions?status=${c.status}` : '/admin/questions'}>
                <Card interactive>
                  <CardContent className="grid gap-1 p-4">
                    <span className="text-caption text-muted-foreground">{c.label}</span>
                    {counts ? (
                      <span className="text-h3 font-semibold tabular-nums">{counts[i] ?? '—'}</span>
                    ) : (
                      <Skeleton className="h-7 w-16" />
                    )}
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {ADMIN_LINKS.filter((l) => l.href !== '/admin').map(({ href, label, icon: Icon }) => (
              <Link key={href} href={href}>
                <Card interactive>
                  <CardContent className="flex items-center gap-3 p-4">
                    <span className="grid size-10 place-items-center rounded-xl bg-primary-subtle text-primary">
                      <Icon className="size-5" aria-hidden="true" />
                    </span>
                    <span className="text-label font-semibold">{label}</span>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </div>
      </div>
    </>
  );
}
