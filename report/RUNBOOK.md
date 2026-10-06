# Tái lập bài lab

Bộ dữ liệu nộp gồm 18 lượt chính thức, 3 lượt skills-auto-dev, 3 skill tự sinh và báo cáo. Điểm thấp hoặc agent hết ngân sách là kết quả âm; trạng thái từng lượt nằm trong REPORT.md, run.json và completion-status.json. Không thay chúng bằng số liệu giả hoặc chạy lại lượt hoàn tất để tăng điểm.

## 1. Môi trường

Host Windows 10, Python 3.11.9, Deep Agents 0.7.21. Các phiên bản khác ở environment.txt. Shell tác vụ dùng Docker Linux/Python 3.11.17; Dockerfile pin digest base image và định danh image ở experiment-manifest.json. Cấu hình alias LAB_MODEL=deepseek:deepseek-chat, temperature=0; callback ở lượt nối lại báo deepseek-flash.

Tạo/activate .venv, pip install -e . và cấu hình .env theo .env.example. .env phải được git bỏ qua; không lưu key vào mã, vết hoặc báo cáo. Mở Docker Desktop rồi xây image:

    docker build -t lab-agent-sandbox:py311 -f validation/Dockerfile.sandbox validation
    $env:PYTHONUTF8='1'
    $env:LAB_TEST_DOCKER='1'
    python -m pytest tests validation --junitxml=report/offline-tests.xml

PYTHONUTF8 hoặc -X utf8 cần cho công cụ cung cấp đọc báo cáo tiếng Việt qua Git trên Windows; không sửa scripts/. Có 52 kiểm thử đạt, gồm kiểm tra SDK sync/async với HTTP MockTransport và 4 kiểm tra cách ly Docker; các test này không gọi API.

Container chỉ mount sandbox, tắt mạng, root filesystem chỉ đọc và không nhận key. File tools cùng sandbox. PATHS_NOTE dùng đường dẫn tương đối workspace/ hoặc skills/; tìm tệp bằng glob/grep file tools. Chỉ bản sao .py được chuẩn hóa LF trước khi agent chạy để phù hợp hash checker; không sửa tasks/ hoặc byte skill.

## 2. Trình tự thí nghiệm trong kho mới

Không chạy lại curator hoặc thay skill của kho đã có tag freeze. Để tái lập toàn bộ quy trình, dùng kho thí nghiệm mới chưa có tag:

    python -u validation/experiment_runs.py --condition baseline --tasks learn
    python -u validation/experiment_runs.py --condition subagents --tasks learn
    python -u validation/run_curator.py
    python -u validation/experiment_runs.py --condition skills-auto --tasks learn --results results-dev
    Copy-Item -LiteralPath results-dev/skills-auto -Destination results/skills-auto-dev -Recurse

Đánh giá nội dung tự sinh theo GUIDE; chỉ xóa skill có hại và chạy curator bổ sung tối đa 2 lần, không sửa tay. Trong bài này đã gọi thật 2 lần, chọn nguyên bộ lần 2; bản gốc/provenance ở curator-history.json, curator-attempt-2/skills và skill-selection.json. Lần đầu bị loại vì gộp schema log vào JSON dữ liệu và lọc missing không đúng phạm vi. Dev của bộ chốt đạt 10/10, 5/8, 9/9 và được giữ riêng.

Sau dev, điền H1-H3 trước khi xem bất kỳ điểm eval nào, cập nhật báo cáo đăng ký, rồi commit và freeze riêng:

    python -X utf8 validation/write_preregistration.py
    git add -- .env.example .gitattributes src validation report results skills
    git commit -m "hypotheses: register H1-H3 before evaluation"
    git commit --allow-empty -m "freeze skills"
    git tag freeze
    python -X utf8 scripts/verify_freeze.py

write_preregistration.py ghi đè bản báo cáo hiện tại và giữ bản trước nối lại ở REPORT.before-resume.md. Chỉ dùng trước eval; không dùng thay báo cáo cuối. Bộ chốt có SHA256 db1d157bfde9f453338dae7b548dd7b3162d89ff84fa942819acb6d6f3ed8e3f; commit hypotheses 56fb1d9 đứng trước freeze 8ec363f. Không tái tạo các tag này trong kho bài nộp.

## 3. Chạy chính thức sau freeze

    python -u validation/experiment_runs.py --condition baseline --tasks eval
    python -u validation/experiment_runs.py --condition subagents --tasks eval
    python -u validation/experiment_runs.py --condition skills-auto --tasks all

Ba batch có thể chạy song song, nhưng mỗi batch có pacing riêng 12 RPM, nên tổng trần lý thuyết là 36 RPM. Mỗi batch dùng 2 worker/tác vụ độc lập và 100 bước; pacing dùng chung coordinator/subagent trong tiến trình. Runner CLI gốc mặc định 60 bước; dùng wrapper trên để tái lập ngân sách thực nghiệm.

Wrapper chỉ retry hạ tầng tạm thời tối đa 1 lượt, lưu lỗi vào results/archive/failed-*. Giữ GraphRecursionError làm kết quả agent không hoàn tất trong 100 bước, không retry theo điểm. SDK sync/async được cấu hình max_retries=0 để không nhân retry 429/503 của wrapper (tối đa 3 lần, chờ 30 giây). Các lượt cũ trước sửa SDK có thể có retry ngầm; không chỉnh hồi tố metrics.

Token callback gồm coordinator/worker, tool_calls/skills_read chỉ luồng chính. Trace được lưu sau mỗi state và bị render_trace cung cấp cắt 1.500 ký tự/message. Usage_by_model ở record mới ghi model provider trả về và cached input; các record cũ chỉ xác nhận alias cấu hình.

## 4. Tổng hợp và kiểm tra bài nộp

    python -X utf8 scripts/verify_freeze.py
    python -X utf8 validation/summarize_experiments.py
    python -X utf8 validation/write_final_report.py
    python -X utf8 validation/audit_submission.py
    python -X utf8 scripts/check_breakdown.py
    git diff --check

summarize_experiments.py sinh table.md bằng nguyên hàm lab.compare, table-usable.md loại lỗi hạ tầng và analysis.json tách learn/eval, technical/rule_, worker và nhiễu. write_final_report.py chỉ đọc dữ liệu, yêu cầu đủ 18 record và freeze kiểm tra đủ 6 lượt skills-auto; giữ nguyên H1-H3 từ commit đăng ký, sinh budget.json/hypothesis-results.json và báo cáo đủ 10 mục.

Audit kiểm tra đủ records/trace/usage, skill hợp lệ/hash, freeze, byte/mã cung cấp giữ nguyên và key không xuất hiện trong tệp git-eligible. Không có phép kiểm tra nào biến điểm thấp thành thành công. Finalize_offline_report.py là công cụ lịch sử cho giai đoạn thiếu API, không dùng khi đã có đầy đủ đánh giá.

## 5. Lặp với bộ đóng băng

Dùng thư mục riêng để giữ nguyên bài nộp:

    python -u validation/experiment_runs.py --condition baseline --tasks all --results results-replication
    python -u validation/experiment_runs.py --condition subagents --tasks all --results results-replication
    python -u validation/experiment_runs.py --condition skills-auto --tasks all --results results-replication
    python -m lab.compare --results results-replication

Không chỉnh/sinh lại skill. Temperature=0 chưa bảo đảm lặp lại; dev và official learn đã dùng cùng hash để đo dao động thô. Một lần mỗi tác vụ không đủ suy rộng hoặc kiểm định thống kê.

## 6. Lịch sử và ngân sách

- previous-config: dữ liệu cũ chưa xác nhận đầy đủ cấu hình; không gộp vào bảng.
- crlf-before-fix/cmd-backend: thử Windows ban đầu có lỗi CRLF/POSIX.
- gitbash-pre-isolation và docker-before-path-enforcement: thử trước cách ly/quy tắc đường dẫn; loại khỏi curator và bảng chính.
- before-api-resume-*: hai lượt subagents lỗi mạng được sao lưu trước thay thế.
- Lượt bị ngắt có thể có vết dở dang và run.json của lượt trước; không cộng chồng bản sao archive.
- Chỉ cộng event finish có usage, curator-history và probe thật; budget.json là cận dưới vì request bị ngắt/phiên cũ có thể thiếu usage. Số token tổng không phải dung lượng một context và không gồm token cuộc trò chuyện Codex. Không suy ra tiền khi chưa có hóa đơn.

## 7. Kiểm tra bộ lọc bổ sung

    python -X utf8 validation/redteam_curator.py

Phản hồi tổng hợp ngoại tuyến, kết quả riêng ở redteam/results.json; không sửa guard cung cấp hay skill đóng băng. Thử 6 trường hợp cho thấy Unicode có thể vượt lọc marker gốc; nhánh NFKC/loại ký tự Cf chặn các trường hợp này và giữ 3 skill benign. Không gọi LLM thật, nên không tuyên bố hoàn thành phép đo jailbreak của DeepSeek theo toàn bộ thử thách 6c.
