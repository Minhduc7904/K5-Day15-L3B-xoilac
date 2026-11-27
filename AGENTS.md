# AGENTS.md — hướng dẫn cho coding agent (Claude Code, Cursor, Codex…) làm việc trong repo này

> Ôn lại: ngày 12 · lab ngày 12. Nhóm sửa file này cho khớp bài của mình (thêm quy ước riêng, bỏ dòng không dùng).

## Repo này là gì

Repo nộp bài hackathon AI20K của nhóm: một bản chạy thử AI cho **một lát cắt** (xem `spec.md` §4), kèm bằng chứng, bộ câu thử và mô phỏng chi phí. Mọi câu trả lời phải chạy được bằng các lệnh dưới đây.

## Bắt đầu phiên làm việc: đồng bộ code và nhánh

Làm bước này **trước khi đọc tài liệu hay sửa bất cứ gì**, để agent không làm trên code cũ hoặc sai nhánh:

1. **Xác định issue.** Lấy số issue từ yêu cầu của người dùng. Không rõ thì hỏi một câu ngắn: "Làm cho issue nào?". Việc không thuộc issue nào (sửa nhỏ, tài liệu, chore) thì dùng nhánh `chore/<mô-tả-ngắn>`.
2. **Kiểm tra thay đổi đang dở.** Chạy `git status`. Có thay đổi chưa commit thì **không** checkout hay pull, báo cho người dùng và hỏi nên commit, stash hay giữ nguyên. Không dùng `git reset --hard`, `git checkout -- .` hay `git clean` để dọn cho xong việc.
3. **Lấy code mới nhất.** `git fetch origin`, rồi `git checkout main` và `git pull --ff-only origin main`. Pull không fast-forward được thì dừng lại, báo người dùng, không tự merge hay rebase.
4. **Vào nhánh của issue.**
   - Nhánh đã có (cục bộ hoặc trên `origin`): `git checkout <nhánh>` rồi `git pull --ff-only`. Nếu nhánh tụt sau `main`, báo người dùng, chưa tự merge `main` vào.
   - Chưa có: tạo từ `main` vừa pull, `git checkout -b feat/issue-<số>-<mô-tả-ngắn>`. Tên chữ thường, có gạch ngang, mô tả ngắn không dấu (ví dụ `feat/issue-2-deploy`). Dùng tiền tố `fix/`, `docs/`, `chore/` thay `feat/` khi hợp hơn.
5. **Báo lại** một dòng: đang ở nhánh nào, ở commit nào, đã pull từ đâu. Rồi mới sang phần "Đọc trước khi làm".

**Người dùng có quyền làm khác quy trình này.** Họ có thể bảo làm ngay trên `main`, dùng nhánh khác, bỏ qua bước pull, hoặc chỉ định cách đặt tên. Khi đó agent làm theo, không từ chối và không bắt người dùng giải thích. Chỉ cần nói ngắn gọn một lần nếu việc đó có rủi ro cụ thể (ví dụ làm trên code chưa pull có thể xung đột), rồi tiếp tục. Quy trình trên là mặc định khi người dùng chưa nói gì.

## Đọc trước khi làm

1. Đọc [AGENTS.md](AGENTS.md), [README.md](README.md), [mục lục và quy chuẩn tài liệu](docs/README.md) và phần liên quan trong [spec.md](spec.md). Riêng việc đụng tới luồng sản phẩm hoặc kiểm thử phải đọc §4 và §7.
2. Đối chiếu yêu cầu hiện tại với issue liên quan nếu có. Tìm `AGENTS.md` gần file sẽ sửa và đọc các quy ước áp dụng trong thư mục đó.
3. Đọc các nguồn theo phạm vi trước khi thiết kế hay chỉnh sửa.

| Phạm vi | Nguồn cần đọc thêm |
| --- | --- |
| Backend, frontend, API, database hoặc MinIO | Đặc tả §4, tài liệu kiến trúc/API liên quan trong [mục lục](docs/README.md) và entry point, schema hoặc module hiện có. |
| Agent, prompt, model hoặc tool | Đặc tả §4, [cách nối model](docs/connect-model.md), và các file liên quan trong `codebase/`. |
| Dữ liệu, benchmark và đánh giá | [Data card](data/DATA_CARD.md), [hướng dẫn eval](eval/README.md), [metric spec](eval/metric_spec.yaml) và đặc tả §7. |
| Deploy, Docker, CI/CD hoặc EC2 | [Runbook EC2](docs/operations/deploy-ec2.md), cấu hình mẫu, Compose và workflow liên quan nếu đã có trong nhánh. |
| Viết hoặc sửa tài liệu | [Quy chuẩn tài liệu](docs/README.md) và template tương ứng trước khi sửa. |

Nếu tài liệu và code mô tả khác nhau, xác minh hành vi tại entry point hoặc cấu hình rồi ghi rõ phần khác biệt khi bàn giao.

## Quy tắc thay đổi chung

- Giữ entry point, hợp đồng API và format đầu ra đã công bố, trừ khi yêu cầu thay đổi chúng. Cập nhật ví dụ và tài liệu tương ứng trong cùng thay đổi.
- Trong backend, giữ trách nhiệm riêng cho API, use case, service và repository. Trong frontend, giữ tổ chức theo feature và dùng lớp gọi API chung của feature. Đọc module hiện có trước khi thêm cấu trúc mới.
- Ghi lệnh hoặc kịch bản đã dùng để kiểm chứng. Với thay đổi chỉ về tài liệu, kiểm liên kết và đối chiếu lệnh mẫu với các entry point thực tế.
- Dùng template đã chọn, tên file chữ thường có dấu gạch ngang và cập nhật mục lục `docs/README.md` khi thêm tài liệu chính. Xem [quy chuẩn đầy đủ](docs/README.md).

## Lệnh

```
python run.py                    # chạy bản chạy thử
python run.py check              # kiểm eval/benchmark.csv + eval/metric_spec.yaml
python run.py eval --try         # thử 3 câu đầu
python run.py eval               # chạy cả bộ → eval/run-N.csv + traces/run-N.jsonl
python run.py score eval/run-N.csv
python run.py simulate --try     # thử mô phỏng chi phí 10 phiên
python run.py simulate           # mô phỏng chi phí → cost/simulate-N.csv
```

Khung chỉ dùng thư viện chuẩn của Python. Thêm thư viện thì ghi vào `requirements.txt`.

## Cấu trúc code

| File | Ai sửa | Hợp đồng |
|---|---|---|
| `codebase/agent.py` | nhóm | `answer(text) -> {"output": str}` — luồng chính, đúng hình dạng ở `spec.md` §4 |
| `codebase/ai.py` | nhóm | `call_model(system, user) -> {"text", "model", "tokens_in", "tokens_out"}`, giữ `@model_call`. Token lấy từ `usage` của API, không ước lượng |
| `codebase/tools.py` | nhóm | mỗi công cụ một hàm có `@tool`, docstring: tên · input · output · có tác động ra ngoài không |
| `codebase/tracing.py`, `eval/run_eval.py`, `cost/simulate.py`, `run.py` | **khung — không sửa** | ghi trace, chạy bộ câu thử, mô phỏng chi phí |

## Luật — agent KHÔNG được làm

- Không commit `.env`, API key, dữ liệu cá nhân thật, nguyên file data BTC cấp.
- Không sửa `eval/run-*.csv`, `cost/simulate-*.csv`, `traces/*` đã chạy (trừ điền cột `pass`, `ghi_chu`).
- Không sửa chuẩn "đạt" (`spec.md` §7), `eval/metric_spec.yaml` sau CP2; không xoá câu thử trượt, không sửa `expected` cho khớp output.
- Không bịa người được phỏng vấn, trích dẫn, câu trả lời khảo sát, số liệu. Số không có nguồn thì ghi rõ *(tự ước tính)*.
- Công cụ có tác động ra ngoài (gửi tin, sửa dữ liệu, chấm điểm): chỉ tạo bản nháp chờ người duyệt.
- Không viết prompt "giấu" câu thử vào code (vd so khớp nguyên văn input của bộ câu thử).

## Quy ước của nhóm

- Ngôn ngữ trả lời người dùng: __
- Phong cách code / đặt tên: __
- Ai duyệt thay đổi do agent tạo trước khi commit: __
