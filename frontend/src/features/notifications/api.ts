import { apiClient } from '@/lib/api-client';

export type Notification = {
  id: number;
  kind: string;
  title: string;
  body: string;
  link: string | null;
  created_at: string;
  read_at: string | null;
};

export type NotificationPage = { items: Notification[]; unread: number; next_before_id: number | null };

const base = '/student/me/notifications';

/** Sự kiện Socket.IO server phát tới room của người dùng khi có thông báo mới (docs/api/realtime-api.md). */
export const NOTIFICATION_EVENT = 'notification:new';

export const notificationApi = {
  async list(limit = 20) {
    return (await apiClient.get<NotificationPage>(base, { params: { limit } })).data;
  },
  async read(id: number) {
    await apiClient.post(`${base}/${id}/read`);
  },
  async readAll() {
    await apiClient.post(`${base}/read-all`);
  },
};
