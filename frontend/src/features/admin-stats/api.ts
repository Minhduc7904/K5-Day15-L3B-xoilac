/** Lớp gọi API thống kê cho admin (#20): GET /api/v1/admin/stats/online-students. */
import { apiClient } from '@/lib/api-client';
import { request } from '@/lib/api-error';

export interface OnlineStudent {
  user_id: number;
  display_name: string | null;
  email: string;
  connections: number;
}

export interface OnlineStats {
  online_students: number;
  connections: number;
  as_of: string;
  users?: OnlineStudent[];
  page?: number;
  page_size?: number;
}

export const adminStatsApi = {
  onlineStudents: (includeUsers = false, page = 1, pageSize = 10) =>
    request<OnlineStats>(() =>
      apiClient.get('/admin/stats/online-students', {
        withCredentials: true,
        params: includeUsers ? { include: 'users', page, page_size: pageSize } : undefined,
      }),
    ),
};
