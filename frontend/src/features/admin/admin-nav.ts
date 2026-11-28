/** Cấu trúc điều hướng khu quản trị: các nhóm hiển thị ở thanh bên và danh sách phẳng cho nơi khác dùng. */
import { FileQuestionMark, FileUp, LayoutDashboard, LayoutTemplate, ListTree, Users, type LucideIcon } from 'lucide-react';

export interface AdminLink {
  href: string;
  label: string;
  icon: LucideIcon;
}

export interface AdminNavGroup {
  id: string;
  label: string;
  links: AdminLink[];
}

export const ADMIN_NAV_GROUPS: AdminNavGroup[] = [
  {
    id: 'phan-tich',
    label: 'Phân tích',
    links: [{ href: '/admin', label: 'Tổng quan', icon: LayoutDashboard }],
  },
  {
    id: 'noi-dung',
    label: 'Nội dung',
    links: [
      { href: '/admin/questions', label: 'Câu hỏi', icon: FileQuestionMark },
      { href: '/admin/chapters', label: 'Chương', icon: ListTree },
      { href: '/admin/pdf-imports', label: 'Nhập đề PDF', icon: FileUp },
      { href: '/admin/exam-templates', label: 'Mẫu cấu trúc đề', icon: LayoutTemplate },
    ],
  },
  {
    id: 'he-thong',
    label: 'Hệ thống',
    links: [{ href: '/admin/users', label: 'Người dùng', icon: Users }],
  },
];

export const ADMIN_LINKS: AdminLink[] = ADMIN_NAV_GROUPS.flatMap((g) => g.links);

export const isActiveLink = (path: string, href: string) =>
  href === '/admin' ? path === '/admin' : path === href || path.startsWith(`${href}/`);

/** Tên mục đang mở, dùng cho thanh trên cùng. */
export const activeLabel = (path: string) => ADMIN_LINKS.find((l) => isActiveLink(path, l.href))?.label;
