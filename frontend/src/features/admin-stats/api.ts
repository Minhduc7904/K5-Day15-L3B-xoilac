/** Lớp gọi API thống kê cho admin (#20): GET /api/v1/admin/stats/online-students. */
import { apiClient } from '@/lib/api-client';
import { request } from '@/lib/api-error';
import { mockMode } from '@/lib/config';

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

const httpAdminStatsApi = {
  onlineStudents: (includeUsers = false, page = 1, pageSize = 10) =>
    request<OnlineStats>(() =>
      apiClient.get('/admin/stats/online-students', {
        withCredentials: true,
        params: includeUsers ? { include: 'users', page, page_size: pageSize } : undefined,
      }),
    ),
};

/** Mock: vài học sinh online, số đổi theo phút để thấy ô tự làm mới. */
const mockAdminStatsApi: typeof httpAdminStatsApi = {
  async onlineStudents(includeUsers = false, page = 1, pageSize = 10) {
    await new Promise((resolve) => window.setTimeout(resolve, 250));
    const minute = new Date().getMinutes();
    const all: OnlineStudent[] = Array.from({ length: 3 + (minute % 4) }, (_, i) => ({
      user_id: 10 + i,
      display_name: `Học sinh ${i + 1}`,
      email: `hocsinh${String(i + 1).padStart(2, '0')}@example.com`,
      connections: i === 0 ? 2 : 1,
    }));
    const stats: OnlineStats = {
      online_students: all.length,
      connections: all.reduce((sum, u) => sum + u.connections, 0),
      as_of: new Date().toISOString(),
    };
    if (!includeUsers) return stats;
    return { ...stats, users: all.slice((page - 1) * pageSize, page * pageSize), page, page_size: pageSize };
  },
};

export const adminStatsApi = mockMode ? mockAdminStatsApi : httpAdminStatsApi;
