# Báo cáo Lab: Self-evolving Agentic

Trạng thái tại đăng ký giả thuyết: đã chạy tập học với baseline/subagents trong Docker. Chưa chạy tập đánh giá. Báo cáo cuối sẽ bổ sung kết quả sau tag freeze; giữ nguyên H1–H3.

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Trần Anh Quân | 2A202602598 | 100% |

- Model: DeepSeek, LAB_MODEL=deepseek:deepseek-chat; temperature=0; recursion_limit=100.
- Host: Windows 10, Python 3.11.9, Deep Agents 0.7.21. Shell tác vụ: Docker Linux, Python 3.11.17; image lab-agent-sandbox:py311. Mỗi shell chỉ thấy thư mục sandbox, tắt mạng và không nhận khóa API; root filesystem chỉ đọc.
- Hai tác vụ độc lập chạy đồng thời; pacing 12 RPM mỗi tiến trình, dùng chung giữa coordinator và worker; 429/503 chờ 30 giây, tối đa 3 lần. Sau nối lại API, chỉ retry lỗi hạ tầng tạm thời; giữ hết ngân sách bước làm kết quả âm, không retry để tăng điểm.
- 52 kiểm thử ngoại tuyến đạt, gồm 4 kiểm thử Docker (tệp dùng chung, không thấy API key/kho, không có mạng và root chỉ đọc, từ chối đường dẫn ngoài sandbox). Đã sửa retry ở cả client SDK sync/async, kiểm chứng bằng HTTP MockTransport và các lượt học thật sau nối lại API.
- Alias cấu hình deepseek-chat; callback ở lượt nối lại báo deepseek-flash. Các bản ghi cũ không lưu identity này, nên so sánh tập học có hạn chế về thời điểm/router. Tất cả lượt đánh giá sẽ chạy cùng cấu hình sau nối lại.
- Các thử ban đầu dùng cấu hình cũ/CMD/Git Bash đã lưu ở results/archive và loại khỏi so sánh chính thức. Có lượt bị dừng chưa đo được usage cuối: ngân sách tổng là cận dưới, không suy ra chi phí tiền từ token.
- Manifest môi trường: report/experiment-manifest.json; phiên bản host: report/environment.txt; nhật ký: report/experiment-events.jsonl.
- Commit freeze sẽ được ghi vào báo cáo cuối sau khi chốt skill và tạo tag, trước khi chạy eval.

## 2. Giả thuyết (commit TRƯỚC tag freeze, Phần 4.0)

- H1 (subagents so với baseline): Dự đoán subagents có điểm kỹ thuật trên tập đánh giá ít nhất ngang baseline nhờ explorer đọc đặc tả và reviewer kiểm tra độc lập; token trung bình cao hơn ít nhất 20%. Không dự đoán worker tự biết quy ước tổ chức chưa được cung cấp. Căn cứ: `guides/pseudocode/02_subagents.md`, vai trò trong `src/lab/subagents.py` và cơ chế ngữ cảnh riêng của công cụ `task` trong `report/tour.txt`.
- H2 (skills-auto so với baseline): Dự đoán skills-auto đạt điểm đánh giá cao nhất và tăng ít nhất 0,15 điểm trung bình so với baseline, chủ yếu nhờ các check `rule_` tái sử dụng quy ước đã học. Không dự đoán đạt mọi quy ước mới. Căn cứ: phản hồi thiếu type hints, regression tests, changelog ở tác vụ học; cơ chế nạp dần theo description trong `guides/pseudocode/05_skill_quality.md` và GUIDE Phần 3.
- H3 (tác vụ học so với tác vụ đánh giá): Dự đoán mức tăng điểm trung bình của skills-auto so với baseline trên tập học lớn hơn mức tăng trên tập đánh giá, vì curator chỉ học quy ước của tập học còn tập đánh giá thêm quy ước mới. Chênh lệch phải được xét cùng nhiễu giữa hai lần chạy cùng skill, và không tự chứng minh quá khớp. Căn cứ: `README.md` mục 2.2 và GUIDE Phần 4.2.

## 3. Làm quen Deep Agents (Phần 0.3)

1. **Bài lab có bao nhiêu agent? Mỗi agent làm gì?** Cấu hình mặc định (`baseline`, `skills-auto`) có **2 vai trò agent**: coordinator nhận yêu cầu, lập kế hoạch, giao việc, kiểm tra và tổng hợp kết quả; worker `general-purpose` thực hiện tác vụ được giao. Cấu hình `subagents` hiện có **5 vai trò**: coordinator, `general-purpose` và 3 worker tự định nghĩa. `explorer` đọc mã, tài liệu và dữ liệu rồi báo cáo, không sửa tệp; `implementer` sửa mã hoặc xử lý dữ liệu/log và chạy kiểm tra; `reviewer` kiểm tra độc lập kết quả và trường hợp biên, không sửa tệp. Đây là số vai trò được cấu hình, không phải số phiên agent thực tế: mỗi lần gọi `task` tạo một phiên worker và coordinator có thể không gọi hết các vai trò. Curator là bước gọi LLM riêng để tạo skill từ phản hồi và vết thất bại của tác vụ học, không phải worker trong cấu hình trên. Bằng chứng: `src/lab/agent.py`, `src/lab/subagents.py`, `src/lab/curator.py` và kết quả `python scripts/tour.py`.

2. **Coordinator giao tiếp với worker agents bằng cách nào?** Coordinator gọi công cụ `task`, chọn worker qua `subagent_type` và gửi nội dung giao việc qua `description`. Thông điệp phải chứa mục tiêu, quy tắc, đường dẫn tệp và thông tin cần thiết vì worker có ngữ cảnh hội thoại riêng, không tự thấy toàn bộ lịch sử của coordinator. Worker thực hiện công việc và trả về báo cáo cuối qua kết quả công cụ; coordinator kiểm tra báo cáo rồi tổng hợp câu trả lời. Các agent còn phối hợp qua tệp trong cùng sandbox: thay đổi tệp của worker có thể được coordinator đọc và kiểm tra. Bằng chứng: `SUBAGENTS_NOTE` trong `src/lab/agent.py` và nguyên tắc cô lập ngữ cảnh trong `guides/pseudocode/02_subagents.md`.

3. **Những công cụ nào được chia sẻ giữa các agent?** Với backend chung và không cấu hình giới hạn `tools` riêng, coordinator và worker dùng các công cụ tệp `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep` và shell `execute` để chạy Python, test hoặc script. Các agent dùng chung tệp trong `workspace/`, nhưng có lịch sử hội thoại riêng. `task` là công cụ giao việc mà coordinator nhìn thấy; quyền giao việc tiếp phụ thuộc cấu hình của worker. Kết quả thực chạy `python scripts/tour.py` liệt kê 9 công cụ ở coordinator gồm 7 công cụ tệp, `execute` và `task`; không có `write_todos` trong danh sách này. Worker `explorer` và `reviewer` được yêu cầu không sửa tệp bằng system prompt, chưa bị khóa quyền ghi bằng tập công cụ riêng. Bằng chứng: `scripts/tour.py`, `src/lab/subagents.py` và `guides/pseudocode/02_subagents.md`.


Bổ sung theo câu hỏi gốc của GUIDE 0.3: system prompt mặc định in ra chuỗi rỗng `''`. Mô tả `task` hướng dẫn: “The agent's report is not shown to the user; relay a summary yourself.” Mô tả `execute` hướng dẫn: “Quote paths containing spaces”. Bằng chứng đầu ra ngoại tuyến lưu tại `report/tour.txt`.

## 4. Đường cơ sở và phân loại lỗi (Phần 2.2)

Chỉ phân loại các check thất bại của tập học chính thức. Lỗi mạng/API/bộ chấm và lượt bị dừng bị loại. GraphRecursionError kèm vết lặp được ghi riêng là thất bại của agent trong ngân sách cố định 100 bước; vẫn chấm workspace dở dang và không coi là lượt hoàn tất thành công.

| Tác vụ | Check thất bại | Nhóm lỗi | Bằng chứng detail |
|---|---|---|---|
| code-learn | rule_type_hints | E — quy ước tổ chức | RULE: every public function (name not starting with '_') in the package has type annotations on all parameters and on the return value. |
| code-learn | rule_regression_tests | E — quy ước tổ chức | RULE: add tests/test_regressions.py with one test function per bug you fixed (at least 3); the file must pass. |
| code-learn | rule_changelog | E — quy ước tổ chức | RULE: record each fix in CHANGELOG.md under the heading '## Unreleased' as a bullet '- fix(<function name>): <short description>' (at least 3 bullets). |
| data-learn | north_q1_revenue | G — chạm ngân sách bước, thiếu đầu ra | FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\admin\\AppData\\Local\\Temp\\lab-0owqlthu\\workspace\\answer.json' |
| data-learn | north_q1_orders | G — chạm ngân sách bước, thiếu đầu ra | FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\admin\\AppData\\Local\\Temp\\lab-0owqlthu\\workspace\\answer.json' |
| data-learn | top_region | G — chạm ngân sách bước, thiếu đầu ra | FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\admin\\AppData\\Local\\Temp\\lab-0owqlthu\\workspace\\answer.json' |
| data-learn | missing_amount_orders | G — chạm ngân sách bước, thiếu đầu ra | FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\admin\\AppData\\Local\\Temp\\lab-0owqlthu\\workspace\\answer.json' |
| data-learn | duplicate_rows_removed | G — chạm ngân sách bước, thiếu đầu ra | FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\admin\\AppData\\Local\\Temp\\lab-0owqlthu\\workspace\\answer.json' |
| data-learn | rule_money_in_cents | G — chạm ngân sách bước, thiếu đầu ra | FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\admin\\AppData\\Local\\Temp\\lab-0owqlthu\\workspace\\answer.json' |
| data-learn | rule_meta_block | G — chạm ngân sách bước, thiếu đầu ra | FileNotFoundError: [Errno 2] No such file or directory: 'C:\\Users\\admin\\AppData\\Local\\Temp\\lab-0owqlthu\\workspace\\answer.json' |
| data-learn | rule_clean_csv | G — chạm ngân sách bước, thiếu đầu ra | RULE: write workspace/clean.csv with the header order_id,timestamp_utc,region,amount_cents; one row per distinct order with a known amount; timestamp_utc as YYYY-MM-DDTHH:MM:SSZ (UTC); region in canonical spelling (North, South, East, West); amount in integer cents. |
| logs-learn | rule_service_names | E — quy ước tổ chức | RULE: service names in the output are lower-case with '-' replaced by '_' (payment-service -> payment_service). |
| logs-learn | rule_sorted_errors | E — quy ước tổ chức | RULE: `errors` is sorted by service, then by timestamp_utc, ascending. |
| logs-learn | rule_schema_header | E — quy ước tổ chức | RULE: the top-level object has "schema_version": 2 and "generated_by": "log-triage". |

## 5. Điều kiện subagents (Phần 2.3)

Explorer đọc đặc tả/dữ liệu; implementer sửa hoặc xử lý và kiểm chứng; reviewer kiểm tra độc lập. Các worker nhận quy ước đường dẫn và chỉ thấy thông điệp giao việc. Explorer/reviewer bị giới hạn bằng prompt, chưa bị khóa công cụ ghi. Vết chỉ chứa luồng chính và báo cáo worker.

| Điều kiện | Tác vụ | Check | Token | Giây | Gọi task |
|---|---|---|---|---|---|
| baseline | code-learn | 7/10 | 70,722 | 112.1 | 0 |
| baseline | data-learn | 0/8 | 772,308 | 282.8 | 0 |
| baseline | logs-learn | 6/9 | 252,481 | 271.6 | 0 |
| subagents | code-learn | 7/10 | 234,572 | 327.5 | 1 |
| subagents | data-learn | 0/8 | 432,725 | 405.8 | 0 |
| subagents | logs-learn | 0/9 | 445,774 | 401.5 | 0 |

## 6. Self-evolving: skill do curator sinh (Phần 3)

Curator chỉ dùng baseline role=learn, phản hồi check thất bại và tối đa 6.000 ký tự cuối vết. Bỏ qua eval, lỗi mạng/API/bộ chấm; cho phép vết agent lặp đến ngân sách bước, có cờ agent_budget_exhausted để phân biệt. Curator thật đã gọi 2 lần (1 lượt bổ sung): lần đầu có skill gộp log/tabular quá rộng và bị loại; lần hai sinh riêng python-package-fix, tabular-data-cleanup, log-triage. Chọn nguyên bộ lần hai, không sửa tay. Các skill dài 12, 14, 15 dòng, có description theo miền; bộ tabular chưa biết metadata của answer.json vì feedback baseline chỉ báo thiếu tệp. Các lượt dev đã hoàn tất và không sửa skill:

| Tác vụ dev | Check | Token | Skill đã đọc |
|---|---|---|---|
| code-learn | 10/10 | 80,015 | 1 |
| data-learn | 5/8 | 107,571 | 3 |
| logs-learn | 9/9 | 92,927 | 1 |

Đã kiểm chứng code và logs thực hiện quy tắc học; data tạo đầu ra nhưng chưa đạt quy ước. Giữ nguyên kết quả này và bộ skill, không dùng dữ liệu đánh giá để cải tiến. Dev sẽ được sao lưu results/skills-auto-dev trước freeze; lần học chính thức sau freeze dùng cùng hash để đo nhiễu.

## 7. Kết quả so sánh (Phần 4)

Chưa chạy eval tại thời điểm đăng ký. Bảng đầy đủ sẽ được lab.compare sinh sau khi freeze và có đủ 18 bản ghi; không thay các ô thiếu bằng số liệu giả.

## 8. Phân tích

Phân tích chính thức sẽ tách learn/eval và kỹ thuật/rule_, đối chiếu skills_read với hành động trong vết, so sánh token và nhiễu giữa skills-auto-dev với cùng bộ skill sau freeze. H1–H3 giữ nguyên dù kết quả phủ định.

## 9. Hạn chế và tính hợp lệ

1. Chỉ ba tác vụ mỗi role và mỗi điều kiện một lượt chính thức; chưa suy rộng ra các miền khác.
2. Temperature=0 vẫn có nhiễu; hai lượt cùng skill trên learn chỉ là ước lượng thô, không phải kiểm định thống kê.
3. Một model và bộ quy ước được thiết kế cho lab; cải thiện rule_ không tự chứng minh tăng năng lực suy luận tổng quát.
4. Vết chỉ ghi luồng chính; token callback gồm worker, tool_calls chỉ đo luồng chính.
5. Các lượt trước cách ly có lỗi môi trường/khám phá ra ngoài sandbox và bị loại; không dùng chúng cho curator hoặc kết luận so sánh. Tổng chi phí còn thiếu các request đang chạy khi dừng.

## 10. Kết luận

Harness, worker, curator và môi trường Docker đã hoạt động. Kết luận hiệu quả học skill sẽ được viết sau thí nghiệm đánh giá, dựa trên dữ liệu và giữ nguyên giả thuyết.

## Phụ lục

Lệnh và lịch sử triển khai ghi trong report/RUNBOOK.md và report/experiment-events.jsonl. Các tệp cung cấp (tests, tasks, scripts, model/tasks/grading/testing/compare và các hằng số/hàm cung cấp) được giữ nguyên. Không commit .env.
