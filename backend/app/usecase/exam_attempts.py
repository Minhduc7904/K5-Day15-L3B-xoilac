from datetime import UTC, datetime, timedelta
from fractions import Fraction
from hashlib import sha256
from json import dumps

from app.models.exam_attempt import ExamAttempt
from app.repositories.exam_attempts import ExamAttemptRepository
from app.repositories.notifications import NotificationRepository
from app.repositories.question_bank_repository import QuestionBankRepository
from app.schemas.exam_attempt import AttemptSave
from app.schemas.exam_chat import DraftItem
from app.service.media_image import load_media_image
from app.usecase.exam_preview_rules import PreviewRuleError
from app.usecase.exam_scoring import allocate_points, grade_question


class AttemptError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code = status, code


def utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def expired(attempt: ExamAttempt, now: datetime) -> bool:
    return attempt.deadline_at is not None and now >= utc(attempt.deadline_at)


class ExamAttempts:
    def __init__(self, repo: ExamAttemptRepository, bank: QuestionBankRepository):
        self.repo, self.bank = repo, bank

    async def _owned(self, user_id, attempt_id):
        attempt = await self.repo.get(attempt_id, user_id)
        if attempt is None:
            raise AttemptError(404, "ATTEMPT_NOT_FOUND", "Không tìm thấy lượt làm bài.")
        return attempt

    @staticmethod
    def _summary(attempt: ExamAttempt) -> dict:
        return {
            "attempt_id": attempt.attempt_id, "draft_id": attempt.draft_id, "status": attempt.status,
            "started_at": utc(attempt.started_at),
            "deadline_at": utc(attempt.deadline_at) if attempt.deadline_at else None,
            "finished_at": utc(attempt.finished_at) if attempt.finished_at else None,
            "reason": attempt.reason, "revision": attempt.revision,
            "answers": attempt.progress.get("answers", {}),
            "question_seconds": {code: ms // 1000 for code, ms in attempt.progress.get("time_ms", {}).items()},
            "current": attempt.progress.get("current"),
            "score": attempt.result["score"] if attempt.result else None,
            "correct": sum(entry["status"] == "correct" for entry in attempt.result["results"]) if attempt.result else 0,
            "total": len(attempt.snapshot["items"]),
        }

    def _state(self, attempt: ExamAttempt, now: datetime) -> dict:
        return {**self._summary(attempt), "server_now": now, "draft": attempt.snapshot}

    async def _snapshot(self, draft):
        try:
            items = allocate_points(draft.items, draft.structure)
        except PreviewRuleError as error:
            raise AttemptError(422, "INVALID_EXAM", str(error)) from None
        source = await self.bank.load_grading_keys([item["question_id"] for item in items])
        private = {}
        usable = []
        for item in items:
            entry = source.get(item["question_id"])
            if entry is None:
                continue
            options = entry["options"]
            stored = item["statements"]
            ids = [option.get("statement_id") for option in stored]
            if any(option_id is None for option_id in ids):
                ids = list(options)
            if len(ids) != len(stored) or any(
                option_id not in options or options[option_id][0] != option["content"]
                for option_id, option in zip(ids, stored)
            ):
                continue
            flags = [options[option_id][1] for option_id in ids]
            kind = item["type"]
            valid = (
                (kind == "SINGLE_CHOICE" and len(flags) > 1 and flags.count(True) == 1
                 and all(type(flag) is bool for flag in flags))
                or (kind == "TRUE_FALSE" and len(flags) == 4 and all(type(flag) is bool for flag in flags))
                or (kind == "SHORT_ANSWER" and bool((entry["answer"] or "").strip()))
            )
            if not valid:
                continue
            private[item["code"]] = {"answer": entry["answer"], "solution": entry["solution"], "statements": flags}
            usable.append(item)
        if not usable:
            raise AttemptError(422, "MISSING_GRADING_KEY", "Đề có câu chưa đủ đáp án để chấm tự động.")
        if len(usable) != len(items):
            # Đề cũ lẫn câu chưa có đáp án: bỏ các câu đó để vẫn làm và chấm được, chia lại điểm trên số câu còn lại.
            try:
                items = allocate_points([{**item, "order": number} for number, item in enumerate(usable, 1)],
                                        draft.structure)
            except PreviewRuleError as error:
                raise AttemptError(422, "INVALID_EXAM", str(error)) from None
        public_items = [{**DraftItem.model_validate(item).model_dump(mode="json"),
                         "points_exact": item["points_exact"]} for item in items]
        snapshot = {
            "draft_id": draft.draft_id, "title": draft.title, "session_id": draft.session_id,
            "preview_version": draft.preview_version, "created_at": utc(draft.created_at).isoformat(),
            "structure": draft.structure, "items": public_items, "shortages": draft.shortages,
            "max_score": 10, "grading_version": 1,
        }
        snapshot["version"] = sha256(dumps(snapshot, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        return snapshot, private

    async def start(self, user_id: int, draft_id: int, restart: bool) -> dict:
        draft = await self.repo.draft(user_id, draft_id, lock=True)
        if draft is None:
            raise AttemptError(404, "EXAM_NOT_FOUND", "Không tìm thấy đề luyện tập.")
        attempt = await self.repo.latest(user_id, draft_id)
        now = await self.repo.clock()
        if attempt and attempt.status == "in_progress":
            await self._expire(attempt, now)
            return self._state(attempt, now)
        if attempt and not restart:
            return self._state(attempt, now)
        snapshot, keys = await self._snapshot(draft)
        now = await self.repo.clock()
        duration = snapshot["structure"].get("duration_minutes") or 0
        attempt = await self.repo.insert(
            user_id=user_id, draft_id=draft_id, started_at=now,
            deadline_at=now + timedelta(minutes=duration) if duration > 0 else None,
            status="in_progress", revision=0, snapshot=snapshot, key=keys, progress={},
        )
        await self.repo.commit()
        return self._state(attempt, now)

    async def summaries(self, user_id: int) -> dict:
        now = await self.repo.clock()
        output = {}
        for draft_id, status, deadline, finished, score in await self.repo.summaries(user_id):
            item = output.setdefault(draft_id, {"active": False, "count": 0, "best_score": None, "last_at": None})
            if status == "in_progress" and (deadline is None or now < utc(deadline)):
                item["active"] = True
            if score is not None:
                item["count"] += 1
                item["best_score"] = score if item["best_score"] is None else max(score, item["best_score"])
                item["last_at"] = item["last_at"] or utc(finished)
        return output

    async def overview(self, user_id: int, draft_id: int) -> dict:
        if await self.repo.draft(user_id, draft_id) is None:
            raise AttemptError(404, "EXAM_NOT_FOUND", "Không tìm thấy đề luyện tập.")
        attempt = await self.repo.latest(user_id, draft_id)
        now = await self.repo.clock()
        if attempt:
            await self._expire(attempt, now)
        history = await self.repo.history(user_id, draft_id)
        return {"latest": self._summary(attempt) if attempt else None,
                "history": [self._summary(row) for row in history]}

    async def read(self, user_id: int, attempt_id: int) -> dict:
        attempt = await self._owned(user_id, attempt_id)
        now = await self.repo.clock()
        await self._expire(attempt, now)
        return self._state(attempt, now)

    @staticmethod
    def _validate_answer(item: dict, answer):
        if answer is None:
            return
        kind = item["type"]
        if kind == "TRUE_FALSE":
            valid = isinstance(answer, list) and len(answer) == len(item["statements"])
        elif kind == "SINGLE_CHOICE":
            valid = isinstance(answer, str) and len(answer) == 1 and 0 <= ord(answer) - 65 < len(item["statements"])
        else:
            valid = isinstance(answer, str)
        if not valid:
            raise AttemptError(422, "INVALID_ANSWER", "Đáp án không hợp lệ cho câu này.")

    async def save(self, user_id: int, attempt_id: int, data: AttemptSave) -> dict:
        attempt = await self._owned(user_id, attempt_id)
        now = await self.repo.clock()
        mutation = str(data.mutation_id)
        if await self.repo.has_mutation(attempt_id, mutation):
            return self._state(attempt, now)
        if attempt.status != "in_progress" or expired(attempt, now):
            await self._expire(attempt, now)
            raise AttemptError(409, "ATTEMPT_FINISHED", "Bài làm đã kết thúc.")
        items = {item["code"]: item for item in attempt.snapshot["items"]}
        if data.question not in items or (data.current is not None and data.current not in items):
            raise AttemptError(422, "INVALID_QUESTION", "Câu hỏi không thuộc lượt làm này.")
        progress = dict(attempt.progress)
        if data.base_revision is not None:
            self._validate_answer(items[data.question], data.answer)
            answers = dict(progress.get("answers", {}))
            revision = answers.get(data.question, {}).get("revision", 0)
            if revision != data.base_revision:
                raise AttemptError(409, "ANSWER_CONFLICT", "Câu này vừa được cập nhật ở tab khác.")
            answers[data.question] = {"value": data.answer, "revision": revision + 1}
            progress["answers"] = answers
        if data.tab_id is not None:
            self._record_time(attempt, progress, data, now)
        self.repo.remember_mutation(attempt_id, mutation)
        attempt.progress = progress
        attempt.revision += 1
        await self.repo.commit()
        return self._state(attempt, now)

    @staticmethod
    def _record_time(attempt, progress, data, now):
        tab_id = str(data.tab_id)
        lease = progress.get("lease", {})
        last = lease.get("at")
        timestamp = now.timestamp()
        same_tab = lease.get("tab") == tab_id
        if last is not None and not same_tab and timestamp - last < 12:
            return
        since = last if same_tab and last is not None else utc(attempt.started_at).timestamp()
        elapsed = min(data.elapsed_ms, max(0, int((timestamp - since) * 1000)))
        times = dict(progress.get("time_ms", {}))
        if elapsed:
            times[data.question] = times.get(data.question, 0) + elapsed
        progress.update(time_ms=times, current=data.current or data.question,
                        lease={} if data.release_tab else {"at": timestamp, "tab": tab_id})

    async def _finish(self, attempt: ExamAttempt, now: datetime, reason: str):
        finished = utc(attempt.deadline_at) if reason == "timeout" else now
        answers = attempt.progress.get("answers", {})
        total, results = Fraction(0), []
        for item in attempt.snapshot["items"]:
            code = item["code"]
            score, status, count = grade_question(item, attempt.key[code], answers.get(code, {}).get("value"))
            total += score
            results.append({"code": code, "points": float(score), "status": status, "tf_correct": count})
        attempt.result = {"score": float(round(total, 2)), "results": results}
        attempt.finished_at, attempt.graded_at, attempt.reason = finished, now, reason
        attempt.status = "graded"
        attempt.revision += 1
        if reason == "timeout":
            # Cùng giao dịch với việc chấm: worker và API mở lại lượt đều đi qua đây, dedupe_key chặn thông báo lặp.
            await NotificationRepository(self.repo.session).add(
                attempt.user_id, "attempt_graded", "Hết giờ, bài đã được tự động nộp và chấm",
                body=f"{attempt.snapshot.get('title') or 'Đề luyện tập'}: {attempt.result['score']:g}/10 điểm.",
                link=f"/results/online-{attempt.attempt_id}", dedupe_key=f"attempt:{attempt.attempt_id}:finished",
                payload={"attempt_id": attempt.attempt_id},
            )
        await self.repo.commit()

    async def _expire(self, attempt: ExamAttempt, now: datetime) -> bool:
        if attempt.status != "in_progress" or not expired(attempt, now):
            return False
        await self._finish(attempt, now, "timeout")
        return True

    async def expire_due(self, attempt_id: int) -> bool:
        attempt = await self.repo.get(attempt_id)
        return bool(attempt and await self._expire(attempt, await self.repo.clock()))

    async def submit(self, user_id: int, attempt_id: int) -> dict:
        attempt = await self._owned(user_id, attempt_id)
        now = await self.repo.clock()
        if attempt.status == "in_progress":
            await self._finish(attempt, now, "timeout" if expired(attempt, now) else "manual")
        return self._state(attempt, now)

    async def result(self, user_id: int, attempt_id: int) -> dict:
        attempt = await self._owned(user_id, attempt_id)
        await self._expire(attempt, await self.repo.clock())
        if attempt.status != "graded":
            raise AttemptError(409, "NOT_GRADED", "Bài làm chưa được nộp.")
        history = await self.repo.history(user_id, attempt.draft_id)
        previous = next((row for row in history if row.attempt_id < attempt_id), None)
        return {"attempt": self._summary(attempt), "draft": attempt.snapshot, "grading": attempt.result,
                "keys": attempt.key, "previous": self._summary(previous) if previous else None}

    async def media(self, user_id: int, attempt_id: int, media_id: int, storage):
        attempt = await self.repo.get(attempt_id, user_id, lock=False)
        marker = f"](media:{media_id})"
        if attempt:
            texts = [item["content"] for item in attempt.snapshot["items"]]
            texts.extend(option["content"] for item in attempt.snapshot["items"] for option in item["statements"])
            if attempt.status == "graded":
                texts.extend(key["solution"] or "" for key in attempt.key.values())
            if any(marker in text for text in texts):
                found = await load_media_image(storage, await self.repo.media_object(media_id))
                if found:
                    return found
        raise AttemptError(404, "MEDIA_NOT_FOUND", "Không tìm thấy ảnh.")
