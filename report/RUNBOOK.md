# Tái lập và kiểm tra bài lab

Cấu hình thí nghiệm đã đo: LAB_MODEL=deepseek:deepseek-chat, temperature=0, recursion_limit=100, pacing 12 RPM mỗi tiến trình. Hai tác vụ độc lập trong mỗi batch dùng chung bộ điều tiết giữa coordinator và worker; các batch có bộ điều tiết riêng. API key đã được người thực hiện gỡ; lượt hoàn thiện cuối chỉ chạy ngoại tuyến. Tệp .env được git bỏ qua.

Hiện có 6/18 bản ghi (2 lượt lỗi kết nối), 2 skill nguyên bản giữ lại từ một lần curator thật và 52 kiểm thử đạt. Chưa chạy skills-auto/dev hoặc eval, chưa commit hypotheses/tag freeze. Phần 2–3 bên dưới là hướng dẫn chạy thật khi có quyền truy cập model, chưa phải các bước đã hoàn thành. Không chạy lệnh API khi chưa cấu hình key.

Sau các lượt đo, đã sửa retry SDK: thay đổi max_retries bằng model_copy chưa cập nhật client khởi tạo sẵn; hiện sao chép cả client sync/async với max_retries=0. Hai test dùng SDK DeepSeek thật với HTTP MockTransport ngoại tuyến xác nhận ngân sách 1 request ban đầu + 3 retry HTTP 429. Các lượt API đã lưu thuộc phiên bản trước sửa; không sửa hồi tố số liệu hoặc khẳng định đã kiểm chứng bản mới bằng API thật.

Host Windows dùng Python 3.11.9/Deep Agents 0.7.21. Shell tác vụ chạy trong Docker Linux với image lab-agent-sandbox:py311. Container chỉ bind mount sandbox, tắt mạng, root filesystem chỉ đọc, không thấy kho nguồn hay API key. Công cụ tệp dùng cùng bản sao sandbox. Backend thực thi đường dẫn shell tương đối theo PATHS_NOTE; tìm tệp bằng glob/grep tools. Chuẩn hóa LF chỉ áp dụng cho bản sao .py trước khi agent bắt đầu, do checker cung cấp dùng hash LF; giữ nguyên tệp nguồn và skill.

## 1. Chuẩn bị

Mở Docker Desktop và chạy PowerShell từ thư mục gốc. Tạo .venv với Python 3.11+, rồi pip install -e . nếu tái dựng môi trường; phiên bản host ở report/environment.txt. Sao chép .env.example thành .env nếu chưa có và điền DEEPSEEK_API_KEY.

    docker build -t lab-agent-sandbox:py311 -f validation/Dockerfile.sandbox validation
    $env:LAB_TEST_DOCKER='1'
    .\.venv\Scripts\python.exe -m pytest tests validation --junitxml=report/offline-tests.xml

Dockerfile dùng digest cố định của base image; định danh image đã chạy ở report/experiment-manifest.json. Kiểm thử dùng model giả, không tốn token. Bốn kiểm thử Docker xác nhận tệp dùng chung, không thấy key/kho, root chỉ đọc/mạng tắt và từ chối đường dẫn ngoài sandbox.

## 2. Thứ tự thí nghiệm tự tiến hóa

Đây là toàn bộ thứ tự theo GUIDE để tái lập trong một kho thí nghiệm mới chưa có tag freeze; không ghi đè skill/tag đã chốt. Đã thực hiện baseline/subagents learn và một lần curator; các lượt subagents code/logs cuối bị lỗi kết nối. Bộ hiện tại chưa freeze nên có thể kiểm tra tiếp theo hướng dẫn phía dưới.

    .\.venv\Scripts\python.exe -u validation/experiment_runs.py --condition baseline --tasks learn
    .\.venv\Scripts\python.exe -u validation/experiment_runs.py --condition subagents --tasks learn
    .\.venv\Scripts\python.exe -u validation/run_curator.py
    .\.venv\Scripts\python.exe -u validation/experiment_runs.py --condition skills-auto --tasks learn --results results-dev
    Copy-Item -LiteralPath results-dev/skills-auto -Destination results/skills-auto-dev -Recurse
    .\.venv\Scripts\python.exe validation/write_preregistration.py
    git add .env.example .gitattributes src/lab/agent.py src/lab/subagents.py src/lab/runner.py src/lab/curator.py src/lab/rate_control.py validation report results skills
    git commit -m "hypotheses: register predictions before evaluation"
    git commit --allow-empty -m "freeze skills"
    git tag freeze
    .\.venv\Scripts\python.exe -u validation/experiment_runs.py --condition baseline --tasks eval
    .\.venv\Scripts\python.exe -u validation/experiment_runs.py --condition subagents --tasks eval
    .\.venv\Scripts\python.exe -u validation/experiment_runs.py --condition skills-auto --tasks all

Curator thật được gọi kèm callback usage để ghi report/curator-run.json; tương đương CLI lab.curator với cùng hàm, model và prompt tại thời điểm gọi. Không chỉnh tay SKILL.md. Skill structured-output-rules đã bị loại vì trộn schema log với JSON dữ liệu và lọc missing quá sớm; bản gốc ở report/rejected-skills. Prompt hiện tại đã cải thiện nhưng chưa gọi lại; không dùng nó để tuyên bố đã tái lập đầu ra lần đầu. Tối đa hai lượt curator bổ sung theo GUIDE. Kết quả dev phải nằm riêng, để bản ghi chính thức results/skills-auto bắt đầu sau freeze.

Để tiếp tục chính bộ hiện tại khi có API, trước tiên sao lưu hai lượt hạ tầng của subagents và chạy lại code-learn/logs-learn với cấu hình Docker/100 bước, giữ các lượt hết ngân sách làm kết quả âm. Sau đó kiểm tra bộ skill trên learn ở results-dev, cập nhật báo cáo và giữ nguyên H1–H3; chỉ commit hypotheses/freeze khi đã chốt bộ skill. Chạy các lượt eval/all theo thứ tự ở trên và cập nhật báo cáo từ dữ liệu thật. Không cần chạy lại baseline hoàn tất để tăng điểm. write_preregistration.py là bản nháp trước eval và sẽ ghi đè báo cáo; phải giữ bản báo cáo hiện tại trước khi dùng.

experiment_runs.py mặc định dùng Docker, 2 worker và giới hạn 100; ghi sự kiện vào report/experiment-events.jsonl. Nó chỉ thử lại tối đa một lượt khi có error, lưu lượt lỗi trong results/archive/failed-*; không thử lại lượt hoàn tất để tăng điểm. Các batch độc lập có thể chạy song song. Vết được cập nhật sau mỗi state; record cuối chứa token của cả coordinator/worker và số tool calls riêng luồng chính.

## 3. Tái chạy với bộ skill đóng băng

Lưu lượt lặp ở thư mục riêng để giữ nguyên kết quả bài nộp:

    .\.venv\Scripts\python.exe -u validation/experiment_runs.py --condition baseline --tasks all --results results-replication
    .\.venv\Scripts\python.exe -u validation/experiment_runs.py --condition subagents --tasks all --results results-replication
    .\.venv\Scripts\python.exe -u validation/experiment_runs.py --condition skills-auto --tasks all --results results-replication
    .\.venv\Scripts\python.exe -m lab.compare --results results-replication

Các lệnh runner gọi API và tính token thật; temperature=0 không bảo đảm điểm lặp lại hoàn toàn. Không sinh lại curator hay sửa skills/auto sau freeze.

## 4. Kiểm tra sản phẩm nộp

    .\.venv\Scripts\python.exe scripts/verify_freeze.py
    .\.venv\Scripts\python.exe validation/summarize_experiments.py
    .\.venv\Scripts\python.exe scripts/check_breakdown.py
    .\.venv\Scripts\python.exe validation/audit_submission.py
    $env:LAB_TEST_DOCKER='1'
    .\.venv\Scripts\python.exe -m pytest tests validation --junitxml=report/offline-tests.xml

summarize_experiments.py sinh report/table.md bằng nguyên hàm lab.compare, thêm table-usable.md loại lỗi hạ tầng và xuất report/analysis.json: điểm/token/thời gian, kỹ thuật/rule_, lỗi học, worker trong vết và nhiễu dev/chính thức. Trước freeze chỉ đọc tập học. audit_submission.py kiểm tra đủ 18 bản ghi/vết, skill hợp lệ/hash, freeze, mã cung cấp không đổi, pattern key thông dụng và giá trị key đã cấu hình trong tệp nộp. Audit hiện báo FAIL do thiếu thực nghiệm và freeze; quét giá trị cấu hình không bao phủ key cũ đã gỡ.

Chốt lại báo cáo ngoại tuyến từ bằng chứng hiện tại (không gọi model):

    .\.venv\Scripts\python.exe validation/summarize_experiments.py
    .\.venv\Scripts\python.exe validation/audit_submission.py
    .\.venv\Scripts\python.exe validation/finalize_offline_report.py

Lệnh audit trả mã 1 khi còn thiếu yêu cầu; vẫn lưu submission-audit.json. Báo cáo ngoại tuyến giữ trạng thái thiếu, không biến kết quả kiểm thử giả thành số liệu API. Finalizer dành cho bộ kết quả chưa hoàn chỉnh hiện tại; sau khi chạy đầy đủ cần viết phân tích mới, không dùng bản báo cáo thiếu này thay cho báo cáo đánh giá.

## 5. Lịch sử môi trường và ngân sách

- results/archive/previous-config: dữ liệu trước, chưa xác nhận đầy đủ model; không gộp vào so sánh DeepSeek.
- crlf-before-fix, cmd-backend: thử Windows ban đầu, hash test sai do CRLF và lệnh POSIX qua CMD.
- gitbash-pre-isolation: agent khám phá ngoài sandbox hoặc lặp đến giới hạn; loại khỏi so sánh và curator.
- docker-before-path-enforcement: thử cách ly trước khi shell thực thi đúng quy tắc đường dẫn; loại khỏi bảng chính thức.
- Bản sao lượt bị dừng có thể chứa vết dở dang và record lượt trước khi lượt hiện tại chưa ghi record cuối. Chỉ cộng các sự kiện finish trong nhật ký vào ngân sách đã đo; không cộng chồng các bản sao archive.
- Tổng token đã đo là cận dưới: thiếu request đang chạy khi dừng, kết nối thử API và lịch sử cũ không có usage đầy đủ. Không quy đổi tiền khi chưa có hóa đơn/cost.

## 6. Thử thách 6c

    .\.venv\Scripts\python.exe validation/redteam_curator.py

Chỉ chạy sau freeze; kết quả ở report/redteam/results.json, không đổi skill chính thức. Dùng phản hồi mô hình tổng hợp có kiểm soát để đo ranh giới lọc rò rỉ Unicode của curator và so với bộ skill thật. Đây không phải tỷ lệ jailbreak của DeepSeek. Chuẩn hóa Unicode chỉ thử ở nhánh kiểm tra riêng.
