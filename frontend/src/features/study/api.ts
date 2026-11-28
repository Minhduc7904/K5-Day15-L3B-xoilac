/**
 * Lớp gọi dữ liệu duy nhất của phần học sinh. Component chỉ gọi `studyApi`, không đụng tới Axios.
 *
 * Mọi dữ liệu đến từ backend. Ngoại lệ duy nhất là `DEMO_RESULT_ID`: trang kết quả minh hoạ cho chặng "Kết quả"
 * của tour hướng dẫn khi học sinh chưa có lượt nào (xem `onboarding/demo-result.ts`).
 * Hồ sơ và credit nằm ở profile/student-account-api.ts.
 */
import { DEMO_RESULT_ID, demoResult } from '../onboarding/demo-result';
import { adaptAttempt, attemptApi } from './attempt-api';
import { loadChapterCatalog } from './chapters';
import { dashboardApi } from './dashboard-api';
import { notFoundError, orNotFound } from './errors';
import { adaptDraft, draftSummary, examChatApi } from './exam-chat-api';

export const studyApi = {
  async getDashboard() {
    const [data] = await Promise.all([dashboardApi.get(), loadChapterCatalog()]);
    return data;
  },
  async listExams() {
    const [drafts, attempts] = await Promise.all([examChatApi.drafts(), attemptApi.summaries(), loadChapterCatalog()]);
    return drafts.map((draft) => {
      const summary = attempts[draft.draft_id];
      return { ...draftSummary(draft), attempts: summary?.count ?? 0, bestScore: summary?.best_score ?? null,
        lastAttemptAt: summary?.last_at ?? null, hasActiveAttempt: summary?.active ?? false };
    });
  },
  async getExam(id: string) {
    if (!/^draft-\d+$/.test(id)) throw notFoundError('Không tìm thấy đề.');
    const [draft, overview] = await Promise.all([
      examChatApi.draft(id.slice('draft-'.length)), orNotFound(attemptApi.overview(id), 'Không tìm thấy đề.'), loadChapterCatalog(),
    ]);
    return { ...adaptDraft(draft), attempts: overview.history.map(adaptAttempt), activeAttempt: overview.latest };
  },
  async getResult(id: string) {
    if (id === DEMO_RESULT_ID) return demoResult();
    if (!/^online-\d+$/.test(id)) throw notFoundError('Không tìm thấy kết quả.');
    const [result] = await Promise.all([
      orNotFound(attemptApi.result(Number(id.slice('online-'.length))), 'Không tìm thấy kết quả.'), loadChapterCatalog(),
    ]);
    return result;
  },
};
