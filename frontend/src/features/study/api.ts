/**
 * Lớp gọi dữ liệu duy nhất của phần học sinh. Component chỉ gọi `studyApi`, không đụng tới mock hay Axios.
 *
 * Đề, lượt làm bài, thống kê và chat tạo đề trên web hiện dùng dữ liệu mẫu.
 * Tích hợp hồ sơ và credit nằm ở profile/student-account-api.ts.
 */
import { liveExamChat } from '@/lib/config';
import { adaptAttempt, attemptApi } from './attempt-api';
import { adaptDraft, draftSummary, examChatApi } from './exam-chat-api';
import { mockStudyApi, runAgent } from './mock';

export const studyApi = {
  ...mockStudyApi,
  async listExams() {
    if (!liveExamChat) return mockStudyApi.listExams();
    const [drafts, attempts] = await Promise.all([examChatApi.drafts(), attemptApi.summaries()]);
    return drafts.map((draft) => {
      const summary = attempts[draft.draft_id];
      return { ...draftSummary(draft), attempts: summary?.count ?? 0, bestScore: summary?.best_score ?? null,
        lastAttemptAt: summary?.last_at ?? null, hasActiveAttempt: summary?.active ?? false };
    });
  },
  async getExam(id: string) {
    if (liveExamChat && id.startsWith('draft-')) {
      const [draft, overview] = await Promise.all([examChatApi.draft(id.slice('draft-'.length)), attemptApi.overview(id)]);
      return { ...adaptDraft(draft), attempts: overview.history.map(adaptAttempt), activeAttempt: overview.latest };
    }
    return { ...await mockStudyApi.getExam(id), activeAttempt: null };
  },
  async getResult(id: string) {
    return liveExamChat && /^online-\d+$/.test(id) ? attemptApi.result(Number(id.slice(7))) : mockStudyApi.getResult(id);
  },
};
export const agentApi = { run: runAgent };

export type { AgentEvent, AgentInput } from './mock';
