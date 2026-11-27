/**
 * Lớp gọi dữ liệu duy nhất của phần học sinh. Component chỉ gọi `studyApi`, không đụng tới mock hay Axios.
 *
 * Đề, lượt làm bài, thống kê và chat tạo đề trên web hiện dùng dữ liệu mẫu.
 * Tích hợp hồ sơ và credit nằm ở profile/student-account-api.ts.
 */
import { mockStudyApi, runAgent } from './mock';

export const studyApi = mockStudyApi;
export const agentApi = { run: runAgent };

export type { AgentEvent, AgentInput } from './mock';
