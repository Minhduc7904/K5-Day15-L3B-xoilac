/** Lớp gọi API của feature realtime: chỉ xin ticket nối socket (POST /auth/socket-ticket, #20). */
import { apiClient } from '@/lib/api-client';
import { request } from '@/lib/api-error';
import { mockMode } from '@/lib/config';
import type { SocketTicket } from './types';

const httpRealtimeApi = {
  socketTicket: () =>
    request<SocketTicket>(() => apiClient.post('/auth/socket-ticket', undefined, { withCredentials: true })),
};

const mockRealtimeApi: typeof httpRealtimeApi = {
  // Chế độ mock không có server socket; useRealtime không gọi hàm này khi mock.
  socketTicket: async () => ({ ticket: 'mock-ticket', expires_in: 30 }),
};

export const realtimeApi = mockMode ? mockRealtimeApi : httpRealtimeApi;
