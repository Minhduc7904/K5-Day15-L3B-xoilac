/**
 * Lớp gọi dữ liệu duy nhất của phần học sinh. Component chỉ gọi `studyApi`, không đụng tới mock hay Axios.
 *
 * Backend chưa có các endpoint này (đề, lượt làm bài, thống kê, chat tạo đề #4), nên hiện luôn dùng mock,
 * kể cả khi tắt `NEXT_PUBLIC_MOCK_MODE`. Khi backend sẵn sàng: viết `httpStudyApi` cùng chữ ký,
 * rồi đổi dòng export dưới đây thành `mockMode ? mockStudyApi : httpStudyApi`.
 */
import { mockStudyApi, runAgent } from './mock';

export const studyApi = mockStudyApi;
export const agentApi = { run: runAgent };

export type { AgentEvent, AgentInput } from './mock';
