"""Write the pre-evaluation report from completed learning runs and predictions."""
import json
from pathlib import Path
import shutil
import xml.etree.ElementTree as ET

from lab.tasks import ROOT


def main():
    report = ROOT / "report" / "REPORT.md"
    old = report.read_text(encoding="utf-8")
    backup = ROOT / "report" / "REPORT.before-resume.md"
    if not backup.exists():
        shutil.copy2(report, backup)
    familiarization = old.split("## 3. Làm quen Deep Agents (Phần 0.3)\n", 1)[1].split("## 4.", 1)[0]
    hypotheses = (ROOT / "report" / "hypotheses.md").read_text(encoding="utf-8")
    hypotheses = "\n".join(line for line in hypotheses.splitlines() if line.startswith("- H"))
    suites = ET.parse(ROOT / "report" / "offline-tests.xml").getroot().findall("testsuite")
    test_count = sum(int(s.get("tests", 0)) - int(s.get("skipped", 0)) for s in suites)
    assert not any(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
    dev = [json.loads((ROOT / "results-dev" / "skills-auto" / task / "run.json").read_text(encoding="utf-8"))
           for task in ("code-learn", "data-learn", "logs-learn")]
    assert all(not r["error"] for r in dev)
    dev_rows = "\n".join(f"| {r['task']} | {r['passed']}/{r['total']} | {r['tokens']['total']:,} | {r['skills_read']} |" for r in dev)
    runs = []
    for condition in ("baseline", "subagents"):
        for task in ("code-learn", "data-learn", "logs-learn"):
            r = json.loads((ROOT / "results" / condition / task / "run.json").read_text(encoding="utf-8"))
            assert r["error"] is None or r["error"].startswith("GraphRecursionError:")
            runs.append(r)
    failures = []
    for r in runs:
        if r["condition"] != "baseline":
            continue
        for c in r["checks"]:
            if not c["passed"]:
                group = "G — chạm ngân sách bước, thiếu đầu ra" if r["error"] else "E — quy ước tổ chức"
                detail = c["detail"].replace("|", "\\|")
                failures.append(f"| {r['task']} | {c['name']} | {group} | {detail} |")
    rows = [f"| {r['condition']} | {r['task']} | {r['passed']}/{r['total']} | {r['tokens']['total']:,} | {r['seconds']} | {r['subagent_calls']} |" for r in runs]
    content = f"""# Báo cáo Lab: Self-evolving Agentic

Trạng thái tại đăng ký giả thuyết: đã chạy tập học với baseline/subagents trong Docker. Chưa chạy tập đánh giá. Báo cáo cuối sẽ bổ sung kết quả sau tag freeze; giữ nguyên H1–H3.

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Trần Anh Quân | 2A202602598 | 100% |

- Model: DeepSeek, LAB_MODEL=deepseek:deepseek-chat; temperature=0; recursion_limit=100.
- Host: Windows 10, Python 3.11.9, Deep Agents 0.7.21. Shell tác vụ: Docker Linux, Python 3.11.17; image lab-agent-sandbox:py311. Mỗi shell chỉ thấy thư mục sandbox, tắt mạng và không nhận khóa API; root filesystem chỉ đọc.
- Hai tác vụ độc lập chạy đồng thời; pacing 12 RPM mỗi tiến trình, dùng chung giữa coordinator và worker; 429/503 chờ 30 giây, tối đa 3 lần. Sau nối lại API, chỉ retry lỗi hạ tầng tạm thời; giữ hết ngân sách bước làm kết quả âm, không retry để tăng điểm.
- {test_count} kiểm thử ngoại tuyến đạt, gồm 4 kiểm thử Docker (tệp dùng chung, không thấy API key/kho, không có mạng và root chỉ đọc, từ chối đường dẫn ngoài sandbox). Đã sửa retry ở cả client SDK sync/async, kiểm chứng bằng HTTP MockTransport và các lượt học thật sau nối lại API.
- Alias cấu hình deepseek-chat; callback ở lượt nối lại báo deepseek-flash. Các bản ghi cũ không lưu identity này, nên so sánh tập học có hạn chế về thời điểm/router. Tất cả lượt đánh giá sẽ chạy cùng cấu hình sau nối lại.
- Các thử ban đầu dùng cấu hình cũ/CMD/Git Bash đã lưu ở results/archive và loại khỏi so sánh chính thức. Có lượt bị dừng chưa đo được usage cuối: ngân sách tổng là cận dưới, không suy ra chi phí tiền từ token.
- Manifest môi trường: report/experiment-manifest.json; phiên bản host: report/environment.txt; nhật ký: report/experiment-events.jsonl.
- Commit freeze sẽ được ghi vào báo cáo cuối sau khi chốt skill và tạo tag, trước khi chạy eval.

## 2. Giả thuyết (commit TRƯỚC tag freeze, Phần 4.0)

{hypotheses}

## 3. Làm quen Deep Agents (Phần 0.3)

{familiarization.strip()}

## 4. Đường cơ sở và phân loại lỗi (Phần 2.2)

Chỉ phân loại các check thất bại của tập học chính thức. Lỗi mạng/API/bộ chấm và lượt bị dừng bị loại. GraphRecursionError kèm vết lặp được ghi riêng là thất bại của agent trong ngân sách cố định 100 bước; vẫn chấm workspace dở dang và không coi là lượt hoàn tất thành công.

| Tác vụ | Check thất bại | Nhóm lỗi | Bằng chứng detail |
|---|---|---|---|
{chr(10).join(failures)}

## 5. Điều kiện subagents (Phần 2.3)

Explorer đọc đặc tả/dữ liệu; implementer sửa hoặc xử lý và kiểm chứng; reviewer kiểm tra độc lập. Các worker nhận quy ước đường dẫn và chỉ thấy thông điệp giao việc. Explorer/reviewer bị giới hạn bằng prompt, chưa bị khóa công cụ ghi. Vết chỉ chứa luồng chính và báo cáo worker.

| Điều kiện | Tác vụ | Check | Token | Giây | Gọi task |
|---|---|---|---|---|---|
{chr(10).join(rows)}

## 6. Self-evolving: skill do curator sinh (Phần 3)

Curator chỉ dùng baseline role=learn, phản hồi check thất bại và tối đa 6.000 ký tự cuối vết. Bỏ qua eval, lỗi mạng/API/bộ chấm; cho phép vết agent lặp đến ngân sách bước, có cờ agent_budget_exhausted để phân biệt. Curator thật đã gọi 2 lần (1 lượt bổ sung): lần đầu có skill gộp log/tabular quá rộng và bị loại; lần hai sinh riêng python-package-fix, tabular-data-cleanup, log-triage. Chọn nguyên bộ lần hai, không sửa tay. Các skill dài 12, 14, 15 dòng, có description theo miền; bộ tabular chưa biết metadata của answer.json vì feedback baseline chỉ báo thiếu tệp. Các lượt dev đã hoàn tất và không sửa skill:

| Tác vụ dev | Check | Token | Skill đã đọc |
|---|---|---|---|
{dev_rows}

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
"""
    report.write_text(content, encoding="utf-8")
    print("Wrote pre-evaluation report; predictions preserved.")


if __name__ == "__main__":
    main()
