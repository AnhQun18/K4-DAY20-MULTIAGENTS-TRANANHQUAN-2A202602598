# Báo cáo Lab: Self-evolving Agentic

Trạng thái: **đã hoàn tất 18/18 lượt chính thức và 3 lượt skill-dev, đăng ký H1–H3 trước đánh giá, đóng băng 3 skill tự sinh và kiểm tra freeze**. Có 5 lượt agent chạm giới hạn 100 bước, được giữ nguyên như kết quả âm có vết và chấm workspace dở dang; không trình bày là thành công. Các lượt lỗi mạng/môi trường trước đó nằm trong archive, không gộp vào bảng chính thức. Báo cáo dùng kết quả API thật; kiểm thử ngoại tuyến được ghi riêng.

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Trần Anh Quân | 2A202602598 | 100% |

- Alias: LAB_MODEL=deepseek:deepseek-chat; temperature=0; recursion_limit=100. Callback ở lượt nối lại API báo deepseek-flash. Lượt đánh giá của cả ba điều kiện dùng cùng phiên cấu hình sau sửa retry SDK; các bản ghi học cũ không có identity trả về nên chỉ xác nhận alias cấu hình.
- Host Windows 10/Python 3.11.9, Deep Agents 0.7.21. Shell tác vụ Docker Linux/Python 3.11.17 với image lab-agent-sandbox:py311; định danh image và phiên bản ở experiment-manifest.json/environment.txt.
- Container chỉ mount sandbox, tắt mạng, root filesystem chỉ đọc, không nhận API key. Công cụ tệp và shell dùng cùng bản sao; shell kiểm tra đường dẫn tương đối. Chuẩn hóa LF trên bản sao Python trước chạy để phù hợp checker Windows; mã tác vụ gốc và byte skill được giữ nguyên.
- 2 worker/tác vụ độc lập mỗi batch, pacing 12 RPM mỗi tiến trình dùng chung main/subagent. Các batch chính thức chạy song song nên tổng trần lý thuyết 36 RPM. HTTP 429/503 chờ 30 giây, tối đa 3 retry; client SDK sync/async không retry ngầm. Lượt hạ tầng được chạy lại tối đa 1 lần, không retry do hết ngân sách hoặc điểm thấp.
- **52 kiểm thử đạt**, gồm 29 test cung cấp, test pacing/retry thật qua MockTransport và 4 test Docker. MockTransport không gọi API và không được tính vào điểm thí nghiệm.
- Đã ghi 38 lượt task finish qua các giai đoạn, 2 lần curator thật, 18 lượt task chính thức + 3 dev. Token chính thức: **4,505,323**; tổng đã đo kể cả thử nghiệm/retry/curator/probe ít nhất **11,609,812** input+output. Chưa bao gồm usage không trả về khi ngắt và lịch sử cũ ngoài nhật ký; không quy đổi tiền.
- Commit hypotheses: 56fb1d9197332b8b3fe9e65750d5786d8114a47b; freeze: 8ec363f0f56f3e8257f1ddadc8fafbf90ea7902f, thời điểm 2026-10-06T16:43:42+07:00. Hash skill: db1d157bfde9f453338dae7b548dd7b3162d89ff84fa942819acb6d6f3ed8e3f. Kiểm tra cung cấp: **checked 6 runs of skill conditions: OK**.

## 2. Giả thuyết (commit TRƯỚC tag freeze, Phần 4.0)

Giữ nguyên câu chữ từ hypotheses.md và commit đăng ký; không sửa dự đoán sau khi thấy điểm eval.

- H1 (subagents so với baseline): Dự đoán subagents có điểm kỹ thuật trên tập đánh giá ít nhất ngang baseline nhờ explorer đọc đặc tả và reviewer kiểm tra độc lập; token trung bình cao hơn ít nhất 20%. Không dự đoán worker tự biết quy ước tổ chức chưa được cung cấp. Căn cứ: `guides/pseudocode/02_subagents.md`, vai trò trong `src/lab/subagents.py` và cơ chế ngữ cảnh riêng của công cụ `task` trong `report/tour.txt`.
- H2 (skills-auto so với baseline): Dự đoán skills-auto đạt điểm đánh giá cao nhất và tăng ít nhất 0,15 điểm trung bình so với baseline, chủ yếu nhờ các check `rule_` tái sử dụng quy ước đã học. Không dự đoán đạt mọi quy ước mới. Căn cứ: phản hồi thiếu type hints, regression tests, changelog ở tác vụ học; cơ chế nạp dần theo description trong `guides/pseudocode/05_skill_quality.md` và GUIDE Phần 3.
- H3 (tác vụ học so với tác vụ đánh giá): Dự đoán mức tăng điểm trung bình của skills-auto so với baseline trên tập học lớn hơn mức tăng trên tập đánh giá, vì curator chỉ học quy ước của tập học còn tập đánh giá thêm quy ước mới. Chênh lệch phải được xét cùng nhiễu giữa hai lần chạy cùng skill, và không tự chứng minh quá khớp. Căn cứ: `README.md` mục 2.2 và GUIDE Phần 4.2.

## 3. Làm quen Deep Agents (Phần 0.3)

1. **Bài lab có bao nhiêu agent? Mỗi agent làm gì?** Cấu hình mặc định (`baseline`, `skills-auto`) có **2 vai trò agent**: coordinator nhận yêu cầu, lập kế hoạch, giao việc, kiểm tra và tổng hợp kết quả; worker `general-purpose` thực hiện tác vụ được giao. Cấu hình `subagents` hiện có **5 vai trò**: coordinator, `general-purpose` và 3 worker tự định nghĩa. `explorer` đọc mã, tài liệu và dữ liệu rồi báo cáo, không sửa tệp; `implementer` sửa mã hoặc xử lý dữ liệu/log và chạy kiểm tra; `reviewer` kiểm tra độc lập kết quả và trường hợp biên, không sửa tệp. Đây là số vai trò được cấu hình, không phải số phiên agent thực tế: mỗi lần gọi `task` tạo một phiên worker và coordinator có thể không gọi hết các vai trò. Curator là bước gọi LLM riêng để tạo skill từ phản hồi và vết thất bại của tác vụ học, không phải worker trong cấu hình trên. Bằng chứng: `src/lab/agent.py`, `src/lab/subagents.py`, `src/lab/curator.py` và kết quả `python scripts/tour.py`.

2. **Coordinator giao tiếp với worker agents bằng cách nào?** Coordinator gọi công cụ `task`, chọn worker qua `subagent_type` và gửi nội dung giao việc qua `description`. Thông điệp phải chứa mục tiêu, quy tắc, đường dẫn tệp và thông tin cần thiết vì worker có ngữ cảnh hội thoại riêng, không tự thấy toàn bộ lịch sử của coordinator. Worker thực hiện công việc và trả về báo cáo cuối qua kết quả công cụ; coordinator kiểm tra báo cáo rồi tổng hợp câu trả lời. Các agent còn phối hợp qua tệp trong cùng sandbox: thay đổi tệp của worker có thể được coordinator đọc và kiểm tra. Bằng chứng: `SUBAGENTS_NOTE` trong `src/lab/agent.py` và nguyên tắc cô lập ngữ cảnh trong `guides/pseudocode/02_subagents.md`.

3. **Những công cụ nào được chia sẻ giữa các agent?** Với backend chung và không cấu hình giới hạn `tools` riêng, coordinator và worker dùng các công cụ tệp `ls`, `read_file`, `write_file`, `edit_file`, `delete`, `glob`, `grep` và shell `execute` để chạy Python, test hoặc script. Các agent dùng chung tệp trong `workspace/`, nhưng có lịch sử hội thoại riêng. `task` là công cụ giao việc mà coordinator nhìn thấy; quyền giao việc tiếp phụ thuộc cấu hình của worker. Kết quả thực chạy `python scripts/tour.py` liệt kê 9 công cụ ở coordinator gồm 7 công cụ tệp, `execute` và `task`; không có `write_todos` trong danh sách này. Worker `explorer` và `reviewer` được yêu cầu không sửa tệp bằng system prompt, chưa bị khóa quyền ghi bằng tập công cụ riêng. Bằng chứng: `scripts/tour.py`, `src/lab/subagents.py` và `guides/pseudocode/02_subagents.md`.


Bổ sung theo câu hỏi gốc của GUIDE 0.3: system prompt mặc định in ra chuỗi rỗng `''`. Mô tả `task` hướng dẫn: “The agent's report is not shown to the user; relay a summary yourself.” Mô tả `execute` hướng dẫn: “Quote paths containing spaces”. Bằng chứng đầu ra ngoại tuyến lưu tại `report/tour.txt`.

## 4. Đường cơ sở và phân loại lỗi (Phần 2.2)

Chỉ dùng baseline learn trong cấu hình Docker cuối. Lỗi FileNotFoundError ở check là hệ quả thiếu đầu ra khi agent hết bước, không đủ để suy ra sai thuật toán hoặc đã biết/vi phạm schema. Phản hồi có RULE cụ thể được dùng học quy ước; feedback thiếu answer.json không tiết lộ meta đầy đủ.

| Tác vụ | Check thất bại | Nhóm lỗi | Bằng chứng detail/vết |
|---|---|---|---|
| code-learn | rule_type_hints | E — quy ước tổ chức | RULE: every public function (name not starting with '_') in the package has type annotations on all parameters and on the return value. |
| code-learn | rule_regression_tests | E — quy ước tổ chức | RULE: add tests/test_regressions.py with one test function per bug you fixed (at least 3); the file must pass. |
| code-learn | rule_changelog | E — quy ước tổ chức | RULE: record each fix in CHANGELOG.md under the heading '## Unreleased' as a bullet '- fix(<function name>): <short description>' (at least 3 bullets). |
| data-learn | north_q1_revenue | G — hết ngân sách, thiếu đầu ra | FileNotFoundError: answer.json chưa được tạo |
| data-learn | north_q1_orders | G — hết ngân sách, thiếu đầu ra | FileNotFoundError: answer.json chưa được tạo |
| data-learn | top_region | G — hết ngân sách, thiếu đầu ra | FileNotFoundError: answer.json chưa được tạo |
| data-learn | missing_amount_orders | G — hết ngân sách, thiếu đầu ra | FileNotFoundError: answer.json chưa được tạo |
| data-learn | duplicate_rows_removed | G — hết ngân sách, thiếu đầu ra | FileNotFoundError: answer.json chưa được tạo |
| data-learn | rule_money_in_cents | G — hết ngân sách, thiếu đầu ra | FileNotFoundError: answer.json chưa được tạo |
| data-learn | rule_meta_block | G — hết ngân sách, thiếu đầu ra | FileNotFoundError: answer.json chưa được tạo |
| data-learn | rule_clean_csv | G — hết ngân sách, thiếu đầu ra | RULE: write workspace/clean.csv with the header order_id,timestamp_utc,region,amount_cents; one row per distinct order with a known amount; timestamp_utc as YYYY-MM-DDTHH:MM:SSZ (UTC); region in canonical spelling (North, South, East, West); amount in integer cents. |
| logs-learn | rule_service_names | E — quy ước tổ chức | RULE: service names in the output are lower-case with '-' replaced by '_' (payment-service -> payment_service). |
| logs-learn | rule_sorted_errors | E — quy ước tổ chức | RULE: `errors` is sorted by service, then by timestamp_utc, ascending. |
| logs-learn | rule_schema_header | E — quy ước tổ chức | RULE: the top-level object has "schema_version": 2 and "generated_by": "log-triage". |

Có 6 lỗi E trực tiếp trên code/logs và 8 check thất bại dây chuyền trên data (G). Riêng hai lượt baseline hoàn tất đạt kỹ thuật **13/13**, quy ước **0/6**; cả sáu lỗi đều là E. Code đạt bảo toàn test, docstring, giá, half-up và CSV; logs đạt UTC, exception/repeat/thống kê. Không có bằng chứng A–D ở hai lượt này; không suy rộng sang data, không đếm tám check thiếu đầu ra là tám nguyên nhân độc lập. Vết data lặp chẩn đoán dòng trùng thay vì ghi answer.json/clean.csv trước giới hạn; quy trình giới hạn chẩn đoán và kiểm chứng tệp là ứng viên cải tiến.

## 5. Điều kiện subagents (Phần 2.3)

| Worker | Vai trò | Lý do thiết kế |
|---|---|---|
| explorer | Đọc đặc tả/schema/dữ liệu, không sửa tệp | Giảm bỏ sót ràng buộc |
| implementer | Sửa/xử lý và chạy kiểm chứng | Tập trung thực hiện thay đổi |
| reviewer | Kiểm tra độc lập, không sửa tệp | Đối chiếu đầu ra/trường hợp biên |

Các worker nhận PATHS_NOTE qua system prompt và chỉ thấy ngữ cảnh giao việc; dùng chung tệp sandbox. Explorer/reviewer được yêu cầu chỉ đọc bằng prompt, chưa khóa quyền ghi bằng tools. Trace chỉ ghi luồng chính và báo cáo worker; khi arguments bị cắt, không suy đoán loại worker. Số gọi task của từng lượt ở mục 7; worker xác định được từ vết: {"code-eval": {"truncated-in-trace": 1}, "code-learn": {"truncated-in-trace": 1}, "data-eval": {}, "data-learn": {}, "logs-eval": {}, "logs-learn": {}}.

Ở code-learn, coordinator đã giao việc một lần; vết ghi mục tiêu sửa package theo docstring, đường dẫn workspace và cấm sửa tests, cùng mã nguồn. Coordinator đọc lại pricing/export/report và chạy test/kiểm chứng độc lập trước kết luận. Arguments dài bị cắt 1.500 ký tự nên không chứng minh toàn bộ quy tắc đã được truyền. Ba quy ước tổ chức vẫn không đạt: chúng chưa có trong đề/context của worker. Lượt logs-learn lặp tìm skills/ không tồn tại, hết bước và không delegation; là kết quả âm thực tế, không phải mô hình giả.

## 6. Self-evolving: skill do curator sinh (Phần 3)

Curator chỉ dùng baseline role=learn, failed-check detail và tối đa 6.000 ký tự cuối vết; bỏ lỗi mạng, giữ hết ngân sách với cờ agent_budget_exhausted. Đã gọi thật 2 lần (1 rerun trong mức GUIDE cho phép), dùng 17,669 token. Lần đầu sinh 3 skill hợp lệ định dạng, nhưng structured-output-rules trộn schema log vào JSON dữ liệu và lọc missing quá sớm; đã loại và lưu nguyên bản. Lần hai sinh bộ tách miền, thay bộ cũ và giữ nguyên byte từ output curator. Provenance: curator-history.json, curator-attempt-2/skills, skill-selection.json. Không chỉnh tay hoặc tái sinh sau freeze.

| Skill | Mức tổng quát | Đúng/sai và phạm vi | Độ dài/description |
|---|---|---|---|
| python-package-fix | Sửa Python theo docstring, kiểm tra source và quy ước tổ chức | Type hints, tên regression file, changelog khớp feedback code; ít nhất 3 vẫn là quy ước lab, không phải quy tắc mọi repo | 12 dòng; kích hoạt khi sửa package Python |
| tabular-data-cleanup | Kiểm tra/dedup/canonicalize/UTC/money, tạo và đọc lại artifact | Quy trình hữu ích nhưng không có meta schema cụ thể vì baseline chưa tạo answer; yêu cầu money cents có thể bị chỉ áp vào CSV; tệp clean phải lọc unknown theo feedback | 14 dòng; kích hoạt CSV/tabular aggregation |
| log-triage | Parse entries/traceback/repeat/UTC, canonical service/sort/schema | Khớp feedback logs; không áp schema log sang JSON khác. Không bao phủ mọi quy ước mới của eval | 15 dòng; kích hoạt JSON triage log |

Trước freeze, dev đạt code 10/10, data 5/8, logs 9/9; skills_read lần lượt 1/3/1 và skills_modified=false. Code thêm hints/regression/changelog, logs chuẩn hóa các quy ước học. Data đọc cả ba skill nhưng answer vẫn dùng tiền float, tự thêm schema_version/generated_by không đúng meta, và CSV chứa dòng unknown có amount trống; ba rule_ không đạt. Đọc skill không đồng nghĩa làm theo hoặc biết schema chưa có trong nguồn học. Giữ nguyên kết quả dev, không dùng phản hồi eval để chỉnh skill.

## 7. Kết quả so sánh (Phần 4.3, 4.4)

Bảng do nguyên hàm lab.compare sinh từ đủ 18 record. GraphRecursionError là kết quả workspace trong giới hạn 100 bước; các mean dưới đây gồm những lượt đó, không diễn giải là tất cả agent đã hoàn tất.

| Task | baseline | subagents | skills-auto |
|---|---|---|---|
| code-learn | 7/10 | 7/10 | 10/10 |
| data-learn | 0/8 | 0/8 | 5/8 |
| logs-learn | 6/9 | 0/9 | 9/9 |
| code-eval | 7/11 | 7/11 | 10/11 |
| data-eval | 5/9 | 0/9 | 5/9 |
| logs-eval | 6/10 | 0/10 | 9/10 |
| **Mean score - learning tasks** | 0.46 | 0.23 | 0.88 |
| **Mean score - evaluation tasks** | 0.60 | 0.21 | 0.79 |
| **Mean tokens per run** | 261,679 | 394,991 | 94,215 |
| **Runs that read a skill** | 0/6 | 0/6 | 6/6 |

| Điều kiện | Role | Mean score | Kỹ thuật | Quy ước | Mean token | Mean giây | Gọi task |
|---|---|---|---|---|---|---|---|
| baseline | learn | 0.456 | 13/18 | 0/9 | 365,170 | 222.2 | 0 |
| baseline | eval | 0.597 | 18/18 | 0/12 | 158,189 | 177.2 | 0 |
| subagents | learn | 0.233 | 7/18 | 0/9 | 371,024 | 378.3 | 1 |
| subagents | eval | 0.212 | 7/18 | 0/12 | 418,960 | 372.0 | 1 |
| skills-auto | learn | 0.875 | 18/18 | 6/9 | 97,371 | 113.2 | 0 |
| skills-auto | eval | 0.788 | 18/18 | 6/12 | 91,061 | 106.1 | 0 |

| Điều kiện | Tác vụ | Check | Token | Giây | Tool calls chính | Gọi task | Đọc skill | Trạng thái |
|---|---|---|---|---|---|---|---|---|
| baseline | code-eval | 7/11 | 46,722 | 87.6 | 19 | 0 | 0 | Hoàn tất |
| baseline | code-learn | 7/10 | 70,722 | 112.1 | 20 | 0 | 0 | Hoàn tất |
| baseline | data-eval | 5/9 | 257,859 | 252.7 | 30 | 0 | 0 | Hoàn tất |
| baseline | data-learn | 0/8 | 772,308 | 282.8 | 51 | 0 | 0 | Hết ngân sách 100 bước |
| baseline | logs-eval | 6/10 | 169,985 | 191.4 | 29 | 0 | 0 | Hoàn tất |
| baseline | logs-learn | 6/9 | 252,481 | 271.6 | 30 | 0 | 0 | Hoàn tất |
| subagents | code-eval | 7/11 | 262,286 | 272.7 | 29 | 1 | 0 | Hoàn tất |
| subagents | code-learn | 7/10 | 234,572 | 327.5 | 25 | 1 | 0 | Hoàn tất |
| subagents | data-eval | 0/9 | 540,297 | 486.4 | 54 | 0 | 0 | Hết ngân sách 100 bước |
| subagents | data-learn | 0/8 | 432,725 | 405.8 | 52 | 0 | 0 | Hết ngân sách 100 bước |
| subagents | logs-eval | 0/10 | 454,297 | 356.9 | 53 | 0 | 0 | Hết ngân sách 100 bước |
| subagents | logs-learn | 0/9 | 445,774 | 401.5 | 53 | 0 | 0 | Hết ngân sách 100 bước |
| skills-auto | code-eval | 10/11 | 63,704 | 92.6 | 22 | 0 | 1 | Hoàn tất |
| skills-auto | code-learn | 10/10 | 80,119 | 117.2 | 22 | 0 | 1 | Hoàn tất |
| skills-auto | data-eval | 5/9 | 124,272 | 116.2 | 15 | 0 | 3 | Hoàn tất |
| skills-auto | data-learn | 5/8 | 105,812 | 127.1 | 16 | 0 | 3 | Hoàn tất |
| skills-auto | logs-eval | 9/10 | 85,207 | 109.5 | 12 | 0 | 1 | Hoàn tất |
| skills-auto | logs-learn | 9/9 | 106,181 | 95.2 | 13 | 0 | 1 | Hoàn tất |

Đầu ra công cụ cung cấp:

```text
condition     role    technical  house rules  mean tokens  read a skill
baseline      eval     18/18         0/12         158,188      0/3
baseline      learn    13/18         0/9          365,170      0/3
subagents     eval      7/18         0/12         418,960      0/3
subagents     learn     7/18         0/9          371,023      0/3
skills-auto   eval     18/18         6/12          91,061      3/3
skills-auto   learn    18/18         6/9           97,370      3/3
```

Các lượt có error: baseline/data-learn, subagents/data-eval, subagents/data-learn, subagents/logs-eval, subagents/logs-learn. Tất cả 18 lượt có trace/usage và skills_modified=false; không còn lượt lỗi mạng trong bảng chính thức. Lượt mạng/môi trường bị thay thế được giữ archive; không chọn theo điểm. Kiểm tra freeze đối chiếu đủ 6 lượt skills-auto, đúng hash và timestamp sau tag. Một số lượt học cũ trước sửa SDK nên tính chi phí học cần xét hạn chế ở mục 9.

## 8. Phân tích

1. **Học và đánh giá:** skills-auto tăng mean learn **+0.419**, mean eval **+0.191** so với baseline. H1: Không phù hợp đầy đủ; kỹ thuật subagents eval 7/18 so với baseline 18/18, token ratio 2.65 lần. H2: Phù hợp; skills-auto đạt điểm eval cao nhất, chênh lệch +0.191 so với ngưỡng dự đoán 0,15. H3: Phù hợp về số điểm quan sát; gain learn +0.419 và eval +0.191. Đây là đối chiếu dự đoán trên mẫu nhỏ, không phải kiểm định thống kê hoặc chứng minh quan hệ nhân quả.

2. **Kỹ thuật/quy ước:** so sánh tách check ở bảng dưới. Nhóm học lại quy ước giúp kiểm tra cơ chế self-evolving, nhóm mới cho thấy giới hạn tổng quát. Check mới của skills-auto: code/rule_version_bump: không đạt; data/rule_sorted_keys_format: không đạt; logs/rule_source_line: không đạt. Không thể suy ra skill biết quy ước mới chỉ vì description phù hợp.

| Họ | Check eval | Loại | baseline | subagents | skills-auto |
|---|---|---|---|---|---|
| code | rule_type_hints | Đã có trên learn | Không đạt | Không đạt | Đạt |
| code | rule_regression_tests | Đã có trên learn | Không đạt | Không đạt | Đạt |
| code | rule_changelog | Đã có trên learn | Không đạt | Không đạt | Đạt |
| code | rule_version_bump | Mới trên eval | Không đạt | Không đạt | Không đạt |
| data | rule_money_in_cents | Đã có trên learn | Không đạt | Không đạt | Không đạt |
| data | rule_meta_block | Đã có trên learn | Không đạt | Không đạt | Không đạt |
| data | rule_clean_csv | Đã có trên learn | Không đạt | Không đạt | Không đạt |
| data | rule_sorted_keys_format | Mới trên eval | Không đạt | Không đạt | Không đạt |
| logs | rule_service_names | Đã có trên learn | Không đạt | Không đạt | Đạt |
| logs | rule_sorted_errors | Đã có trên learn | Không đạt | Không đạt | Đạt |
| logs | rule_schema_header | Đã có trên learn | Không đạt | Không đạt | Đạt |
| logs | rule_source_line | Mới trên eval | Không đạt | Không đạt | Không đạt |

3. **Đọc và làm theo:** code là ví dụ được hỗ trợ: baseline thiếu rule_type_hints/regression/changelog, dev đọc python-package-fix rồi thực sự thêm các artifact; ba rule đạt. Logs dev đọc log-triage và đạt chuẩn service/sort/schema. Data là ví dụ không đủ: đọc cả ba skill nhưng tiền answer vẫn float, meta bị đoán và clean CSV gồm unknown. Các check data của skills-auto còn thất bại: data-learn/rule_money_in_cents, data-learn/rule_meta_block, data-learn/rule_clean_csv, data-eval/rule_money_in_cents, data-eval/rule_meta_block, data-eval/rule_clean_csv, data-eval/rule_sorted_keys_format. Chi tiết official và checker là bằng chứng quyết định; skills_read chỉ đếm main-thread read_file, không quan sát bên trong worker.

4. **Chi phí:** mean token eval lần lượt baseline 158,189, subagents 418,960, skills-auto 91,061. Điểm/1.000 token tương ứng 0.003776, 0.000506, 0.008656. Tỷ lệ này tính cả lượt hết ngân sách; chưa đủ để kết luận chi phí đa tác tử đáng giá ở mọi tác vụ. Delegation cần gắn với check và hành động, không chỉ tên condition. Token gồm main/worker, tool_calls chỉ luồng chính, thời gian gồm pacing/retry/Docker. Không quy đổi token thành tiền khi thiếu hóa đơn và phần cached input.

5. **Rò rỉ/quá khớp:** nguồn curator chỉ baseline learn, không eval; hai lần tuyển chọn diễn ra trước tag, không sửa byte sau freeze. Validator không thấy marker eval trong 3 skill; giữ schema/filenames quy ước được feedback cho phép, không giữ đáp án học. Gain học lớn hơn eval nếu có chỉ là dấu hiệu cần đối chiếu nhiễu, độ khó và thay đổi router, không tự chứng minh quá khớp. Bộ lọc marker không chặn mọi Unicode/diễn đạt lại.

6. **Nhiễu cùng skill:** dev và official learn có cùng hash; so sánh từng tác vụ dưới đây. Cả ba cặp đều có delta score bằng 0; chưa quan sát biến động điểm, nhưng token và thời gian khác nhau. Điều này không chứng minh phương sai bằng 0. Hai lượt mỗi tác vụ chỉ là ước lượng thô; chênh lệch gần mức dao động này cần thận trọng, và temperature=0 không bảo đảm lặp lại hoàn toàn.

| Tác vụ | Dev | Official | Delta score | Token dev | Token official | Cùng hash |
|---|---|---|---|---|---|---|
| code-learn | 10/10 | 10/10 | +0.000 | 80,015 | 80,119 | Có |
| data-learn | 5/8 | 5/8 | +0.000 | 107,571 | 105,812 | Có |
| logs-learn | 9/9 | 9/9 | +0.000 | 92,927 | 106,181 | Có |

## 9. Hạn chế và tính hợp lệ

1. Chỉ ba tác vụ mỗi role, một lượt chính thức mỗi cấu hình và hai lượt cùng skill trên learn. Một vòng lặp có thể làm lệch mean; không có khoảng tin cậy/kiểm định để suy rộng.
2. Lượt baseline/subagents học cũ trước nối lại API dùng cùng alias nhưng chưa lưu model trả về; callback mới báo deepseek-flash. Đã sửa SDK retries giữa hai giai đoạn; vì vậy gain/chi phí học có nhiễu cấu hình và thời điểm. Toàn bộ eval dùng phiên sau sửa, nên phần đối chứng eval đồng nhất hơn.
3. House rules do giảng viên thiết kế và chỉ một alias model. Đạt quy ước học không tự chứng minh năng lực suy luận tổng quát; metadata chưa được feedback khi answer thiếu là giới hạn quan trọng của curator.
4. Các GraphRecursionError có partial workspace chấm được nhưng không phải lượt thành công; nhiều check thiếu tệp cùng một nguyên nhân. Không nhầm giảm token của lượt thất bại với tiết kiệm để hoàn thành tác vụ.
5. Trace cung cấp cắt 1.500 ký tự mỗi message, không có worker internals. Không xác minh toàn bộ delegation dài hoặc mọi bước suy luận; usage callback có thể thiếu request bị ngắt trước trả số liệu.
6. Shell native/Git Bash không cách ly ở mức OS; chỉ kết quả Docker cuối được đưa vào so sánh. Giới hạn path thao tác và container không bảo đảm chống mọi mã độc, nhưng test chứng minh không chuyển key, mount giới hạn và mạng tắt trong cấu hình này.
7. Thử bộ lọc bằng 6 phản hồi tổng hợp: guard gốc nhận 2/5 phản hồi độc hại; nhánh chuẩn hóa Unicode nhận 0/5. Ba skill đóng băng hợp lệ ở cả hai guard. Không dùng guard thử vào thí nghiệm chính và không đo tỷ lệ jailbreak của DeepSeek; đây là phép thử ngoại tuyến ranh giới validator.

## 10. Kết luận

Đã hoàn tất 18 lượt chính thức, 3 dev và 52 kiểm thử với freeze xác minh đủ 6 lượt skills-auto. Skills-auto có mean eval 0.788, so với baseline 0.597 và subagents 0.212; các rule học lại ở code/logs cho thấy cơ chế tuyển chọn skill hoạt động trong lab. Data và các quy ước mới còn giới hạn như checker/vết ở mục 8, nên không kết luận skill luôn đúng hoặc đa tác tử luôn tốt hơn. Giữ nguyên kết quả hết ngân sách và dao động dev/official thay vì chạy lại để nâng điểm. Cải tiến tiếp theo là đo lặp thêm trên cùng snapshot model và kiểm chứng việc áp dụng quy tắc theo từng artifact trước khi tạo một bộ skill mới trong thí nghiệm riêng.

## Phụ lục

- Lệnh/thứ tự: RUNBOOK.md. Nhật ký thật: experiment-events.jsonl; ngân sách: budget.json. Curator history và selection giữ provenance đầu ra tự động.
- Báo cáo đăng ký trước: git show 56fb1d9197332b8b3fe9e65750d5786d8114a47b:report/REPORT.md; H1–H3 final được so khớp nguyên văn bằng write_final_report.py. Không viết lại giả thuyết sau eval.
- Dữ liệu dev giữ ở results/skills-auto-dev; official ở results/<condition>/<task>. results-dev là bản làm việc ban đầu, không gộp trùng vào bảng/chi phí.
- Windows chạy scripts/verify_freeze.py bằng Python -X utf8 để đọc báo cáo tiếng Việt từ Git; không sửa script cung cấp. Mã tests/tasks/scripts/model/tasks/grading/testing/compare và AST hằng số/hàm cung cấp được audit đối chiếu gốc d982034.
- Kiểm tra cuối bằng submission-audit.json, offline-tests.xml và completion-status.json. .env git-ignored; quét key cấu hình/pattern trước commit, không lưu key vào artifact.
