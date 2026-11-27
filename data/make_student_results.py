"""Sinh data/student_results.csv — kết quả làm bài của học sinh MẪU, TỰ DỰNG (synthetic).

Không dùng dữ liệu học sinh thật. Mã câu lấy từ data/question_bank.csv (mẫu trong repo).
Chạy:  python data/make_student_results.py     (seed cố định → luôn ra cùng file)

Hồ sơ (khớp data/DATA_CARD.md và eval/benchmark.csv):
  HS01  chương yếu nhất 12C1 (40% đúng), các chương khác ≥ 70%           (B01, B02, B03, B07, B08, B09–B13)
  HS02  chưa có dòng nào                                                  (B05)
  HS03  dữ liệu mâu thuẫn: nhiều câu có 2 dòng cùng lượt, kết quả trái nhau (B06)
  HS04  hai chương yếu gần nhau: 11C6 (45% đúng), 12C4 (50% đúng)         (B04)
"""
import csv
import os
import random
from collections import defaultdict

SEED = 42
HERE = os.path.dirname(os.path.abspath(__file__))
BANK = os.path.join(HERE, "question_bank.csv")
OUT = os.path.join(HERE, "student_results.csv")

# (chương, số câu làm, số câu đúng): mỗi chương chia đều qua các lượt
PROFILES = {
    "HS01": {"luot": 4, "chapters": [("12C1", 20, 8), ("12C4", 20, 16), ("11C6", 16, 12), ("12C2", 12, 10), ("12C5", 12, 10)]},
    "HS04": {"luot": 4, "chapters": [("11C6", 20, 9), ("12C4", 20, 10), ("12C1", 20, 16), ("12C2", 12, 10), ("12C5", 12, 10), ("11C1", 12, 10)]},
}
# HS03: mỗi chương làm n câu; trong đó `flip` câu có thêm một dòng cùng lượt với kết quả trái nhau
HS03 = {"luot": 2, "chapters": [("12C1", 12, 8), ("12C4", 12, 8), ("11C6", 12, 8), ("12C5", 12, 8)]}


def load_bank():
    by_chapter = defaultdict(list)
    with open(BANK, encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            by_chapter[r["chuong"].split(";")[0]].append(r["ma_cau"])
    return by_chapter


def split_even(items, parts):
    return [items[i::parts] for i in range(parts)]


def main():
    rnd = random.Random(SEED)
    bank = load_bank()
    rows = []

    for hs, prof in sorted(PROFILES.items()):
        for ch, n, k in prof["chapters"]:
            qids = rnd.sample(sorted(bank[ch]), n)
            verdict = ["dung"] * k + ["sai"] * (n - k)
            rnd.shuffle(verdict)
            pairs = list(zip(qids, verdict))
            for luot, part in enumerate(split_even(pairs, prof["luot"]), start=1):
                for q, v in part:
                    rows.append((hs, luot, q, ch, v))

    # HS03: mâu thuẫn — 8/12 câu mỗi chương có 2 dòng cùng lượt, kết quả trái nhau
    for ch, n, flip in HS03["chapters"]:
        qids = rnd.sample(sorted(bank[ch]), n)
        pairs = []
        for i, q in enumerate(qids):
            v = rnd.choice(["dung", "sai"])
            pairs.append((q, v))
            if i < flip:
                pairs.append((q, "sai" if v == "dung" else "dung"))
        # chia theo câu (không tách hai dòng của một câu sang lượt khác)
        by_q = defaultdict(list)
        for q, v in pairs:
            by_q[q].append(v)
        for idx, (q, vs) in enumerate(by_q.items()):
            luot = idx % HS03["luot"] + 1
            for v in vs:
                rows.append(("HS03", luot, q, ch, v))

    rows.sort(key=lambda r: (r[0], r[1], r[3], r[2], r[4]))
    with open(OUT, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ma_hs", "luot", "ma_cau", "chuong", "ket_qua"])
        w.writerows(rows)

    # tóm tắt để kiểm
    print("Đã ghi %s: %d dòng (seed %d)" % (OUT, len(rows), SEED))
    stat = defaultdict(lambda: defaultdict(lambda: [0, 0]))
    for hs, luot, q, ch, v in rows:
        stat[hs][ch][1] += 1
        stat[hs][ch][0] += v == "dung"
    for hs in sorted(stat):
        print(hs, {ch: "%d/%d" % tuple(x) for ch, x in sorted(stat[hs].items())})
    print("HS02: không có dòng nào (chưa có lịch sử)")
    seen = defaultdict(set)
    for hs, luot, q, ch, v in rows:
        seen[(hs, luot, q)].add(v)

    total_q = defaultdict(int)
    conf_q = defaultdict(int)
    for (hs, luot, q), s in seen.items():
        total_q[hs] += 1
        conf_q[hs] += len(s) > 1
    for hs in sorted(total_q):
        print("  %s: %d/%d câu có kết quả trái nhau trong cùng lượt" % (hs, conf_q[hs], total_q[hs]))


if __name__ == "__main__":
    main()
