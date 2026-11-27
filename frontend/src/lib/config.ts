export const mockMode = process.env.NEXT_PUBLIC_MOCK_MODE === 'true'
  || (process.env.NEXT_PUBLIC_MOCK_MODE !== 'false' && process.env.NODE_ENV === 'development');

export const liveExamChat = !mockMode && process.env.NEXT_PUBLIC_EXAM_CHAT_LIVE === 'true';

export const apiBaseUrl = '/api/v1';
