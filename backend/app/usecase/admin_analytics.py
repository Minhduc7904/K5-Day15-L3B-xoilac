"""Thống kê phân tích cho dashboard admin: tăng trưởng, học tập, ngân hàng câu hỏi, vận hành.

Chỉ đọc và chỉ trả số tổng hợp (không email, không tên). Ngày tính theo múi giờ Việt Nam, giống dashboard học sinh.
Các hàm `*_stats` là hàm thuần trên dữ liệu đã nạp để kiểm thử không cần cơ sở dữ liệu.
"""
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, date, datetime, time, timedelta
from statistics import median

from app.core.study_time import STUDY_TZ
from app.repositories.admin_analytics_repository import AdminAnalyticsRepository
from app.repositories.question_bank_repository import QuestionBankRepository

RANGES = (7, 30, 90)
DIFFICULTIES = ("NB", "TH", "VD", "VDC")
MIN_CHAPTER_ANSWERS = 5  # chương có ít hơn số câu này không xếp hạng tỉ lệ đúng (mẫu quá nhỏ)
TOP_N = 10
IN_FLIGHT_IMPORT = {"queued", "processing"}
FAILED_IMPORT = "failed"


# ---- thời gian -------------------------------------------------------------------------------------------


def aware(instant: datetime) -> datetime:
    return instant if instant.tzinfo else instant.replace(tzinfo=UTC)


def local_day(instant: datetime) -> date:
    return aware(instant).astimezone(STUDY_TZ).date()


def window(today: date, days: int) -> list[date]:
    return [today - timedelta(days=offset) for offset in range(days - 1, -1, -1)]


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def weeks_in(days: Sequence[date]) -> list[date]:
    return sorted({week_start(d) for d in days})


def per_day(days: Sequence[date], events: Iterable[date]) -> list[int]:
    counts = Counter(events)
    return [counts.get(d, 0) for d in days]


def distinct_per_day(days: Sequence[date], pairs: Iterable[tuple[int, date]]) -> list[int]:
    seen: dict[date, set[int]] = defaultdict(set)
    for user_id, day in pairs:
        seen[day].add(user_id)
    return [len(seen.get(d, ())) for d in days]


def since_utc(today: date, days: int, extra: int = 0) -> datetime:
    """Mốc đầu ngày (giờ Việt Nam) lùi `days + extra` ngày, đổi sang UTC để so với cột thời gian."""
    start = datetime.combine(today - timedelta(days=days - 1 + extra), time.min, STUDY_TZ)
    return start.astimezone(UTC)


def _iso(days: Sequence[date]) -> list[str]:
    return [d.isoformat() for d in days]


# ---- chương ----------------------------------------------------------------------------------------------


def top_chapter(code: str | None, catalog: dict[str, dict]) -> str | None:
    """Mã chương gốc (cấp cao nhất) của một mã chương. Mã lạ không có trong danh mục giữ nguyên."""
    if not code:
        return None
    for _ in range(10):  # cây chương nông; chặn vòng lặp nếu dữ liệu hỏng
        parent = (catalog.get(code) or {}).get("parent_code")
        if not parent:
            break
        code = parent
    return code


def chapter_name(code: str, catalog: dict[str, dict]) -> str:
    return (catalog.get(code) or {}).get("name") or code


# ---- tính toán thuần -------------------------------------------------------------------------------------


def activity_pairs(logins: Iterable[tuple[int, datetime]], attempts: Sequence[dict]) -> list[tuple[int, date]]:
    """Một học sinh "hoạt động" ngày D khi có phiên đăng nhập mới hoặc bắt đầu một bài làm ngày D."""
    pairs = [(user_id, local_day(at)) for user_id, at in logins]
    pairs += [(a["user_id"], local_day(a["started_at"])) for a in attempts]
    return pairs


def trailing_active(days: Sequence[date], pairs: Sequence[tuple[int, date]], span: int) -> list[int]:
    by_user: dict[int, set[date]] = defaultdict(set)
    for user_id, day in pairs:
        by_user[user_id].add(day)
    result = []
    for day in days:
        start = day - timedelta(days=span - 1)
        result.append(sum(any(start <= d <= day for d in seen) for seen in by_user.values()))
    return result


def funnel_stats(cohort: Sequence[tuple[int, datetime, datetime | None]], profiles: set[int],
                 drafters: set[int], attempters: set[int]) -> list[dict]:
    """Phễu lồng nhau: mỗi bước chỉ tính người đã qua bước trước."""
    ids = {user_id for user_id, _, _ in cohort}
    verified = {user_id for user_id, _, verified_at in cohort if verified_at is not None}
    steps = [("registered", "Đăng ký", ids)]
    for key, label, passed in (
        ("verified", "Xác minh email", verified), ("profile", "Hoàn tất hồ sơ", profiles),
        ("drafted", "Tạo đề đầu tiên", drafters), ("attempted", "Làm bài đầu tiên", attempters),
    ):
        steps.append((key, label, steps[-1][2] & passed))
    return [{"key": key, "label": label, "count": len(members)} for key, label, members in steps]


def heatmap(starts: Iterable[datetime]) -> list[list[int]]:
    """Ma trận 7 × 24: hàng là thứ (0 = thứ Hai), cột là giờ trong ngày (giờ Việt Nam)."""
    grid = [[0] * 24 for _ in range(7)]
    for start in starts:
        local = aware(start).astimezone(STUDY_TZ)
        grid[local.weekday()][local.hour] += 1
    return grid


def score_bins(scores: Sequence[float]) -> list[dict]:
    counts = [0] * 10
    for score in scores:
        counts[min(9, max(0, int(score)))] += 1
    return [{"label": f"{i}–{i + 1}", "count": count} for i, count in enumerate(counts)]


def chapter_rates(graded: Sequence[dict], catalog: dict[str, dict]) -> tuple[list[dict], int]:
    """Tỉ lệ làm đúng theo chương gốc, từ thấp lên cao. Trả (danh sách tối đa TOP_N, số chương bị ẩn vì mẫu nhỏ)."""
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for attempt in graded:
        statuses = {r.get("code"): r.get("status") for r in (attempt["result"] or {}).get("results", [])}
        for item in (attempt["snapshot"] or {}).get("items", []):
            codes = item.get("chapter_codes") or []
            raw = codes[0] if codes else (item.get("chapter") or "").split(",")[0].strip()
            root = top_chapter(raw, catalog)
            if root is None:
                continue
            totals[root][1] += 1
            totals[root][0] += statuses.get(item.get("code")) == "correct"
    ranked = [
        {"code": code, "name": chapter_name(code, catalog), "correct": c, "total": t, "rate": c / t}
        for code, (c, t) in totals.items() if t >= MIN_CHAPTER_ANSWERS
    ]
    ranked.sort(key=lambda r: (r["rate"], r["code"]))
    return ranked[:TOP_N], len(totals) - len(ranked)


def coverage_stats(rows: Sequence[tuple], catalog: dict[str, dict]) -> list[dict]:
    """Số câu khả dụng theo chương gốc × độ khó. Chương gốc chưa có câu nào vẫn hiện (ô 0 là điểm cần soạn thêm)."""
    cells: dict[tuple[str, str], set[int]] = defaultdict(set)
    for question_id, difficulty, code, _parent in rows:
        root = top_chapter(code, catalog)
        if root is not None and difficulty in DIFFICULTIES:
            cells[(root, difficulty)].add(question_id)
    roots = {c for c, e in catalog.items() if not e.get("parent_code")} | {root for root, _ in cells}
    result = []
    for code in sorted(roots):
        counts = {d: len(cells.get((code, d), ())) for d in DIFFICULTIES}
        result.append({"code": code, "name": chapter_name(code, catalog),
                       "grade": (catalog.get(code) or {}).get("grade"), "counts": counts, "total": sum(counts.values())})
    return result


def shortage_stats(drafts: Sequence[Sequence[dict]], catalog: dict[str, dict]) -> dict:
    """Chương học sinh yêu cầu nhưng ngân hàng không đủ câu (từ `shortages` của đề nháp)."""
    missing: Counter[str] = Counter()
    occurrences: Counter[str] = Counter()
    for shortages in drafts:
        for s in shortages:
            gap = int(s.get("requested") or 0) - int(s.get("available") or 0)
            if gap <= 0 or not s.get("chapter"):
                continue
            for raw in {c.strip() for c in str(s["chapter"]).split(",") if c.strip()}:
                root = top_chapter(raw, catalog) or raw
                missing[root] += gap
                occurrences[root] += 1
    ranked = sorted(missing, key=lambda c: (-missing[c], c))[:TOP_N]
    return {
        "drafts": len(drafts), "drafts_with_shortage": sum(1 for d in drafts if d),
        "chapters": [{"code": c, "name": chapter_name(c, catalog), "missing": missing[c],
                      "occurrences": occurrences[c]} for c in ranked],
    }


def bank_totals(groups: Sequence[tuple]) -> dict:
    totals: Counter[str] = Counter()
    by_type: Counter[str] = Counter()
    by_grade: Counter[int] = Counter()
    by_difficulty: Counter[str] = Counter()
    for visibility, archived, kind, grade, difficulty, count in groups:
        if archived:
            totals["archived"] += count
            continue
        totals[(visibility or "").lower()] += count
        if visibility == "PUBLISHED":
            by_type[kind or "?"] += count
            if grade is not None:
                by_grade[grade] += count
            by_difficulty[difficulty or "?"] += count
    return {
        "published": totals["published"], "draft": totals["draft"], "private": totals["private"],
        "archived": totals["archived"],
        "by_type": [{"key": k, "count": by_type[k]} for k in sorted(by_type)],
        "by_grade": [{"key": str(g), "count": by_grade[g]} for g in sorted(by_grade)],
        "by_difficulty": [{"key": d, "count": by_difficulty.get(d, 0)} for d in DIFFICULTIES],
    }


def import_success_rate(imports: Sequence[tuple]) -> float | None:
    done = [status for status, _, _ in imports if status not in IN_FLIGHT_IMPORT]
    return None if not done else 1 - done.count(FAILED_IMPORT) / len(done)


# ---- use case --------------------------------------------------------------------------------------------


class AdminAnalytics:
    def __init__(self, repo: AdminAnalyticsRepository, bank: QuestionBankRepository,
                 now: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self._repo = repo
        self._bank = bank
        self._now = now

    def _frame(self, days: int) -> tuple[date, list[date], list[date]]:
        today = local_day(self._now())
        return today, window(today, days), window(today - timedelta(days=days), days)

    async def overview(self, days: int) -> dict:
        today, current, previous = self._frame(days)
        # Lùi thêm 6 ngày để tính được "hoạt động trong 7 ngày" cho ngày đầu của kỳ trước.
        since = since_utc(today, days * 2, extra=6)
        attempts = await self._repo.attempts(since)
        pairs = activity_pairs(await self._repo.logins(since), attempts)
        signups = [local_day(created) for _, created, _ in await self._repo.students_created(since)]
        graded = [a for a in attempts if a["status"] == "graded" and a["finished_at"] is not None]
        finished = [(local_day(a["finished_at"]), (a["result"] or {}).get("score")) for a in graded]
        imports = await self._repo.pdf_imports(since)
        bank = bank_totals(await self._repo.question_groups())
        pdf_drafts = await self._repo.pdf_draft_status()

        def users_in(period: list[date]) -> int:
            return len({user for user, day in pairs if period[0] <= day <= period[-1]})

        def scores_in(period: list[date]) -> list[float]:
            return [s for day, s in finished if s is not None and period[0] <= day <= period[-1]]

        def imports_in(period: list[date]) -> list[tuple]:
            return [i for i in imports if period[0] <= local_day(i[2]) <= period[-1]]

        def mean(values: list[float]) -> float | None:
            return sum(values) / len(values) if values else None

        def finished_in(period: list[date]) -> int:
            return sum(1 for day, _ in finished if period[0] <= day <= period[-1])

        def signups_in(period: list[date]) -> int:
            return sum(1 for day in signups if period[0] <= day <= period[-1])

        now_imports, before_imports = imports_in(current), imports_in(previous)
        kpis = [
            {"key": "active_students", "value": users_in(current), "previous": users_in(previous),
             "series": distinct_per_day(current, pairs)},
            {"key": "new_students", "value": signups_in(current), "previous": signups_in(previous),
             "series": per_day(current, signups)},
            {"key": "completed_attempts", "value": finished_in(current), "previous": finished_in(previous),
             "series": per_day(current, (d for d, _ in finished))},
            {"key": "average_score", "value": mean(scores_in(current)), "previous": mean(scores_in(previous)),
             "series": []},
            {"key": "published_questions", "value": bank["published"], "previous": None, "series": []},
            {"key": "import_success_rate", "value": import_success_rate(now_imports),
             "previous": import_success_rate(before_imports), "series": []},
        ]
        return {
            "range_days": days, "generated_at": aware(self._now()), "kpis": kpis,
            "attention": {
                "pending_pdf_drafts": pdf_drafts.get("pending", 0), "draft_questions": bank["draft"],
                "failed_imports": sum(1 for s, _, _ in now_imports if s == FAILED_IMPORT),
            },
        }

    async def growth(self, days: int) -> dict:
        today, current, _ = self._frame(days)
        since = since_utc(today, days, extra=6)
        attempts = await self._repo.attempts(since)
        pairs = activity_pairs(await self._repo.logins(since), attempts)
        in_window = set(current)
        cohort = [c for c in await self._repo.students_created(since_utc(today, days)) if local_day(c[1]) in in_window]
        dau = distinct_per_day(current, pairs)
        active = len({user for user, day in pairs if day in in_window})
        mix = await self._repo.profile_mix()
        starts = [a["started_at"] for a in attempts if local_day(a["started_at"]) in in_window]
        return {
            "range_days": days, "days": _iso(current),
            "signups": per_day(current, (local_day(c[1]) for c in cohort)),
            "dau": dau, "wau": trailing_active(current, pairs, 7),
            "active_students": active, "stickiness": (sum(dau) / len(dau) / active) if active else None,
            "funnel": funnel_stats(cohort, await self._repo.profile_user_ids(), await self._repo.draft_owner_ids(),
                                   await self._repo.attempt_owner_ids()),
            "heatmap": heatmap(starts),
            "grades": [{"key": str(g), "count": sum(1 for grade, _ in mix if grade == g)} for g in (10, 11, 12)],
            "targets": [{"key": str(t), "count": sum(1 for _, target in mix if target == t)} for t in (7, 8, 9)],
        }

    async def learning(self, days: int) -> dict:
        today, current, _ = self._frame(days)
        in_window = set(current)
        attempts = [a for a in await self._repo.attempts(since_utc(today, days)) if local_day(a["started_at"]) in in_window]
        graded = [a for a in attempts if a["status"] == "graded" and a["result"]]
        scores = [float(a["result"]["score"]) for a in graded]
        weeks = weeks_in(current)
        by_week: dict[date, list[float]] = defaultdict(list)
        outcomes: dict[date, Counter[str]] = defaultdict(Counter)
        for a in attempts:
            week = week_start(local_day(a["started_at"]))
            outcomes[week]["in_progress" if a["status"] != "graded" else (a["reason"] or "manual")] += 1
        for a, score in zip(graded, scores):
            by_week[week_start(local_day(a["started_at"]))].append(score)
        rates, hidden = chapter_rates(graded, await self._bank.chapter_catalog())
        return {
            "range_days": days, "graded": len(graded), "median": median(scores) if scores else None,
            "average": sum(scores) / len(scores) if scores else None, "bins": score_bins(scores),
            "weekly": [{"week": w.isoformat(), "attempts": len(by_week.get(w, ())),
                        "average": (sum(by_week[w]) / len(by_week[w])) if by_week.get(w) else None} for w in weeks],
            "outcomes": [{"week": w.isoformat(), "manual": outcomes[w]["manual"], "timeout": outcomes[w]["timeout"],
                          "in_progress": outcomes[w]["in_progress"]} for w in weeks],
            "chapters": rates, "chapters_hidden": hidden, "min_answers": MIN_CHAPTER_ANSWERS,
        }

    async def bank(self, days: int) -> dict:
        today, _, _ = self._frame(days)
        catalog = await self._bank.chapter_catalog()
        return {
            "range_days": days, **bank_totals(await self._repo.question_groups()),
            "coverage": coverage_stats(await self._repo.coverage(), catalog),
            "shortages": shortage_stats(await self._repo.draft_shortages(since_utc(today, days)), catalog),
        }

    async def operations(self, days: int) -> dict:
        today, current, _ = self._frame(days)
        in_window = set(current)
        since = since_utc(today, days)
        imports = [i for i in await self._repo.pdf_imports(since) if local_day(i[2]) in in_window]
        flight = IN_FLIGHT_IMPORT.__contains__
        moves = [(local_day(at), delta) for at, delta in await self._repo.credit_moves(since)]
        sessions = [(sid, local_day(at)) for sid, at in await self._repo.chat_sessions(since)]
        drafts = await self._repo.drafts_by_session([sid for sid, _ in sessions])
        attempted = await self._repo.attempted_draft_ids([draft_id for _, draft_id in drafts])
        drafted_sessions = {sid for sid, _ in drafts}
        attempted_sessions = {sid for sid, draft_id in drafts if draft_id in attempted}
        return {
            "range_days": days, "days": _iso(current),
            "imports": {
                "total": len(imports), "success_rate": import_success_rate(imports),
                "by_status": [{"key": k, "count": v} for k, v in sorted(Counter(s for s, _, _ in imports).items())],
                "failed_by_stage": [{"key": k, "count": v} for k, v in
                                    sorted(Counter(st for s, st, _ in imports if s == FAILED_IMPORT).items())],
                "completed": per_day(current, (local_day(c) for s, _, c in imports if not flight(s) and s != FAILED_IMPORT)),
                "failed": per_day(current, (local_day(c) for s, _, c in imports if s == FAILED_IMPORT)),
                "in_flight": per_day(current, (local_day(c) for s, _, c in imports if flight(s))),
            },
            "pdf_drafts": await self._repo.pdf_draft_status(),
            "credits": {
                "granted": [sum(d for day, d in moves if day == x and d > 0) for x in current],
                "spent": [sum(-d for day, d in moves if day == x and d < 0) for x in current],
            },
            "chat": {
                "sessions": len(sessions), "with_draft": len(drafted_sessions),
                "with_attempt": len(attempted_sessions), "daily": per_day(current, (day for _, day in sessions)),
            },
        }
