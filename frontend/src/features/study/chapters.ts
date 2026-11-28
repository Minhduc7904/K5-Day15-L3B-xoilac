/**
 * Tên chương lấy từ danh mục thật của backend (`GET /exam-chat/chapters`), nạp một lần và nhớ trong bộ nhớ.
 * `studyApi` đợi `loadChapterCatalog()` trước khi trả dữ liệu, nên khi trang hiện, `chapterOf` đã có tên.
 * Danh mục chưa tải được thì hiện mã chương, không làm hỏng trang.
 */
import { examChatApi } from './exam-chat-api';
import type { Chapter } from './types';

type Entry = { name: string; parent_code: string | null; grade?: number | null };

let catalog: Record<string, Entry> = {};
let loading: Promise<void> | null = null;

export function loadChapterCatalog(): Promise<void> {
  loading ??= examChatApi.chapters().then(
    (data) => {
      catalog = data;
    },
    () => {
      loading = null; // lần gọi sau thử lại
    },
  );
  return loading;
}

const gradeFromCode = (code: string) => Number(/^(\d{1,2})C/.exec(code)?.[1]);

/** Tên chương nhúng sẵn, dành cho trang minh hoạ của tour (mã không có trong danh mục của backend). */
const local: Record<string, Entry> = {};
export function registerChapter(code: string, name: string, grade: number) {
  local[code] = { name, parent_code: null, grade };
}

export function chapterOf(code: string): Chapter {
  const entry = catalog[code] ?? local[code];
  const grade = entry?.grade ?? gradeFromCode(code);
  return { code, name: entry?.name ?? code, grade: (grade === 10 || grade === 11 ? grade : 12) as Chapter['grade'] };
}

/** Mã chương cha của một chương con. Chương cha hoặc mã chưa biết trả về chính nó. */
export const parentOf = (code: string) => catalog[code]?.parent_code ?? code;
