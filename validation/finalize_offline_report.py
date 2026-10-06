"""Finalize a truthful partial lab report from existing artifacts, without API calls."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from lab.tasks import ROOT


def main():
    report_dir = ROOT / "report"
    report_path = report_dir / "REPORT.md"
    previous = report_path.read_text(encoding="utf-8")
    familiarization = previous.split("## 3. Làm quen Deep Agents (Phần 0.3)\n", 1)[1].split("## 4.", 1)[0].strip()
    hypotheses = "\n".join(line for line in (report_dir / "hypotheses.md").read_text(encoding="utf-8").splitlines() if line.startswith("- H"))
    analysis = json.loads((report_dir / "analysis.json").read_text(encoding="utf-8"))
    audit = json.loads((report_dir / "submission-audit.json").read_text(encoding="utf-8"))
    selection = json.loads((report_dir / "skill-selection.json").read_text(encoding="utf-8"))
    curator = json.loads((report_dir / "curator-run.json").read_text(encoding="utf-8"))
    runs = [json.loads(path.read_text(encoding="utf-8")) for condition in ("baseline", "subagents")
            for path in sorted((ROOT / "results" / condition).glob("*-learn/run.json"))]
    events = [json.loads(line) for line in (report_dir / "experiment-events.jsonl").read_text(encoding="utf-8").splitlines() if line]
    finishes = [e for e in events if e["event"] == "finish"]
    probe = json.loads((report_dir / "model-tool-probe.json").read_text(encoding="utf-8"))
    # Usage for the two probe cases was measured separately from task batches.
    probe_tokens = sum(case["usage"]["total_tokens"] for case in probe)
    budget = {"finished_task_attempts": len(finishes), "finished_task_tokens": sum(e.get("tokens", 0) for e in finishes),
              "curator_tokens": curator["tokens"]["total"], "tool_probe_tokens": probe_tokens,
              "token_total_is_lower_bound": True,
              "unmeasured": ["small initial API connection probe", "requests interrupted before usage returned", "older runs outside event history"]}
    budget["measured_tokens_lower_bound"] = budget["finished_task_tokens"] + budget["curator_tokens"] + probe_tokens
    (report_dir / "budget.json").write_text(json.dumps(budget, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    suites = ET.parse(report_dir / "offline-tests.xml").getroot().findall("testsuite")
    tests = {key: sum(int(s.get(key, 0)) for s in suites) for key in ("tests", "failures", "errors", "skipped")}
    assert not tests["failures"] and not tests["errors"], "Fix offline tests before finalizing the report"
    breakdown = subprocess.run([str(ROOT / ".venv" / "Scripts" / "python.exe"), "scripts/check_breakdown.py"],
                               cwd=ROOT, check=True, capture_output=True, text=True).stdout.strip()
    (report_dir / "check-breakdown.txt").write_text(breakdown + "\n", encoding="utf-8")
    failure_rows = []
    categories = Counter()
    for failure in analysis["learning_failures"]:
        missing = "FileNotFoundError" in failure["detail"]
        category = "G" if failure["task"] == "data-learn" else "E"
        categories[category] += 1
        label = "G — thiếu đầu ra khi hết ngân sách bước" if category == "G" else "E — quy ước tổ chức"
        detail = "answer.json chưa được tạo; các check phụ thuộc cùng thất bại" if missing else failure["detail"]
        failure_rows.append(f"| {failure['task']} | {failure['name']} | {label} | {detail.replace('|', '/')} |")
    run_rows = []
    for r in runs:
        status = "Hoàn tất" if not r["error"] else ("Hết ngân sách 100 bước" if r["error"].startswith("GraphRecursionError:") else "Lỗi kết nối; loại khỏi phân tích")
        run_rows.append(f"| {r['condition']} | {r['task']} | {r['passed']}/{r['total']} | {r['tokens']['total']:,} | {r['seconds']} | {r['tool_calls']} | {r['subagent_calls']} | {status} |")
    raw_table = (report_dir / "table.md").read_text(encoding="utf-8").strip()
    usable_table = (report_dir / "table-usable.md").read_text(encoding="utf-8").strip()
    content = f"""# Báo cáo Lab: Self-evolving Agentic

Trạng thái: đã hoàn thiện harness, kiểm thử ngoại tuyến, sinh và tuyển chọn skill bằng curator thật, cùng báo cáo dựa trên số liệu đã lưu. Người thực hiện đã gỡ API key, nên dừng gọi model. **Thực nghiệm chưa đủ yêu cầu nộp hoàn chỉnh:** có 6/18 bản ghi, trong đó 2 lượt lỗi kết nối; chưa có skills-auto/dev, tập đánh giá, commit hypotheses hoặc tag freeze. Không dùng model giả thay kết quả thực nghiệm.

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Trần Anh Quân | 2A202602598 | 100% |

- Model thực chạy: LAB_MODEL=deepseek:deepseek-chat; temperature=0; recursion_limit=100. Các kết quả cấu hình cũ được giữ trong archive và loại khỏi bảng hiện tại.
- Host Windows 10, Python 3.11.9, Deep Agents 0.7.21. Shell tác vụ dùng Docker Linux/Python 3.11.17, image lab-agent-sandbox:py311; định danh image, phiên bản thư viện và phạm vi cấu hình ở experiment-manifest.json/environment.txt.
- Container chỉ mount sandbox, tắt mạng, root filesystem chỉ đọc và không nhận key. Công cụ tệp cùng dùng sandbox. Shell kiểm tra đường dẫn tương đối; Python trong container vẫn truy cập được thư viện của container. Bản sao Python trên Windows được chuẩn hóa LF trước khi agent bắt đầu để phù hợp hash của checker; không sửa mã tác vụ gốc.
- Hai tác vụ độc lập trong mỗi batch, pacing 12 RPM mỗi tiến trình, dùng chung giữa coordinator/worker. Thời gian bao gồm pacing và retry. Runner CLI gốc mặc định 60 bước; thí nghiệm dùng validation/experiment_runs.py với 100 bước.
- Sau các lượt thực nghiệm, rà soát phát hiện model_copy(max_retries=0) chưa đổi client SDK khởi tạo sẵn. Đã sửa sao chép cả client đồng bộ/bất đồng bộ và kiểm thử HTTP 429 bằng MockTransport: đúng 4 request (1 ban đầu + 3 retry), không có mạng. Các lượt thực nghiệm đã lưu dùng phiên bản trước sửa; chưa chạy lại API thật với bản sửa, không cập nhật hồi tố token/thời gian.
- Kiểm thử cuối: **{tests['tests'] - tests['skipped']} passed**, {tests['skipped']} skipped, gồm 29 test cung cấp và kiểm thử bổ sung. Bằng chứng: offline-tests.xml. Docker ban đầu đang tắt; đã khởi động lại và chạy lại bộ test.
- Có {len(finishes)} lượt tác vụ đã ghi sự kiện finish qua các cấu hình, {len(runs)} bản ghi hiện tại; curator thật gọi 1 lần. Ngân sách đã đo ít nhất **{budget['measured_tokens_lower_bound']:,} token**, gồm {budget['finished_task_tokens']:,} token tác vụ, {curator['tokens']['total']:,} token curator và {probe_tokens:,} token probe công cụ. Chưa bao gồm request bị dừng chưa trả usage và lịch sử cũ ngoài nhật ký; không quy đổi thành tiền.
- Chưa tạo freeze vì chưa xác minh bộ skill trên tác vụ học. Tập đánh giá chưa được chạy. Audit báo {audit['status']} do thiếu thực nghiệm/freeze; không đổi trạng thái này thành đạt.

## 2. Giả thuyết (commit TRƯỚC tag freeze, Phần 4.0)

H1–H3 dưới đây giữ nguyên từ hypotheses.md, viết trước khi chạy/xem điểm đánh giá. Chưa có dữ liệu để kiểm chứng và chưa có commit đăng ký.

{hypotheses}

## 3. Làm quen Deep Agents (Phần 0.3)

{familiarization}

## 4. Đường cơ sở và phân loại lỗi (Phần 2.2)

Chỉ dùng baseline tập học với cấu hình Docker cuối. Phân biệt lỗi kết nối với GraphRecursionError: lỗi sau là agent lặp đến giới hạn 100 bước trong khi API vẫn trả lời, nên giữ như thất bại trong ngân sách cố định; không gọi đó là lượt hoàn tất. Không xem check báo thiếu tệp là bằng chứng agent đã hiểu sai công thức hoặc quy ước.

| Tác vụ | Check thất bại | Nhóm lỗi | Bằng chứng detail/vết |
|---|---|---|---|
{chr(10).join(failure_rows)}

Có {categories['E']} lỗi E trực tiếp ở code/logs và {categories['G']} check thất bại dây chuyền ở data do thiếu đầu ra (G). Vì vậy toàn bộ baseline không có đa số lỗi E; trên hai lượt hoàn tất thì cả 6 lỗi đều thuộc E. Hai lượt này đạt kỹ thuật **13/13**, quy ước **0/6**: code đạt mọi check kỹ thuật, gồm docstring/giá/CSV/test gốc; logs đạt UTC, traceback, repeat count và thống kê. Đây là bằng chứng không ủng hộ A–D trên hai lượt hoàn tất; không suy rộng sang data.

Vết data-learn cho thấy lặp các lệnh liệt kê dòng trùng dù đã nhận kết quả; không tạo answer.json/clean.csv trước giới hạn. Một skill giới hạn vòng chẩn đoán và buộc tạo/đọc lại đầu ra có thể giúp, nhưng chưa đo được hiệu quả. rule_money_in_cents/rule_meta_block chỉ báo FileNotFoundError, nên không đủ phản hồi để curator suy ra đầy đủ schema metadata của data.

## 5. Điều kiện subagents (Phần 2.3)

| Worker | Vai trò | Lý do thiết kế |
|---|---|---|
| explorer | Đọc README, docstring, schema và dữ liệu; không sửa tệp | Phát hiện đặc tả và dữ liệu bẩn |
| implementer | Sửa mã/xử lý dữ liệu và chạy kiểm tra | Thực hiện công việc có phạm vi rõ |
| reviewer | Kiểm chứng độc lập; không sửa tệp | Phát hiện sai khác trước kết luận |

Worker nhận PATHS_NOTE và ngữ cảnh riêng qua task.description; explorer/reviewer bị giới hạn bằng prompt, chưa khóa công cụ ghi. Tất cả ba bản ghi hiện tại có **subagent_calls=0**; vết không có giao việc nên không có nội dung truyền thiếu/thừa hoặc báo cáo worker để đánh giá. Đây là lựa chọn thực tế của model dù coordinator được nhắc giao việc; chưa chứng minh lợi ích hay chi phí của các worker.

Chỉ data-learn có cặp không bị lỗi hạ tầng: baseline 0/8, 772.308 token, 282,8 giây; subagents 0/8, 432.725 token, 405,8 giây. Token giảm khoảng 44%, nhưng cả hai đều chạm giới hạn và không gọi worker; không suy ra đa tác tử giúp tiết kiệm. Các lượt code/logs hiện tại bị lỗi kết nối phải loại khỏi so sánh. Lượt code trước đó trong archive cũng hết ngân sách; không chọn kết quả theo điểm.

## 6. Self-evolving: skill do curator sinh (Phần 3)

Curator chỉ lấy baseline role=learn, check thất bại và tối đa 6.000 ký tự cuối vết. Bỏ qua lỗi mạng/provider/checker; giữ vết hết ngân sách với cờ agent_budget_exhausted. Parser/validator cung cấp kiểm tra frontmatter, tên, độ dài và marker đánh giá. **Một lần curator thật**, {curator['seconds']} giây, {curator['tokens']['total']:,} token, sinh 3 skill hợp lệ về định dạng; không chỉnh tay nội dung. Đã loại 1 skill có nguy cơ gây sai, giữ 2. Chưa chạy lại curator vì API đã gỡ; prompt được cải thiện phạm vi nhưng chưa có đầu ra mới. Không đồng nhất prompt hiện tại với prompt đã sinh bộ skill ban đầu.

| Skill | Mức tổng quát | Đúng/sai và quyết định | Độ dài, description và skills_read |
|---|---|---|---|
| repo-conventions | Quy trình cho gói Python; giữ tên test/changelog tổ chức theo GUIDE | Hints, regression tests và changelog phù hợp feedback code; yêu cầu ít nhất 3 phản ánh quy ước lab, chưa chắc hợp mọi repo; giữ nguyên | 11 dòng; description kích hoạt khi sửa Python có test/changelog; chưa đo skills_read |
| verify-before-finish | Quy trình kiểm tra đầu ra trước kết thúc, chống lặp chẩn đoán | Hợp với vết hết ngân sách; ví dụ tên đầu ra được tổng quát qua nhiều họ; yêu cầu checklist không thay thế checker; giữ nguyên | 11 dòng; description nêu lúc chuẩn bị hoàn tất; SKILLS_NOTE yêu cầu đọc skill liên quan từ đầu; chưa đo skills_read |
| structured-output-rules | Gộp tabular data và log-triage; kích hoạt quá rộng | Metadata log schema_version=2/generated_by=log-triage có thể bị áp vào JSON dữ liệu bán hàng; drop missing trước đếm có thể mất thống kê. Loại, lưu nguyên bản ở rejected-skills/ | 14 dòng; chưa đo skills_read; không đưa vào skills/auto hiện tại |

Hash đầu ra curator ban đầu: {selection['original_generated_hash']}. Hash bộ giữ lại: {selection['retained_hash']}. Việc xóa skill theo GUIDE được ghi ở skill-selection.json; không chỉnh byte của hai skill giữ lại. Chưa có dữ liệu skills-auto tập học hoặc dev; chưa chứng minh skill được đọc hay làm theo.

## 7. Kết quả so sánh (Phần 4.3, 4.4)

Bảng nguyên trạng sinh bằng hàm lab.compare, lưu table.md. Công cụ có sẵn không lọc error; hai ô code/logs của subagents và trung bình chứa lỗi mạng, **không dùng để kết luận**. Thiếu toàn bộ skills-auto và eval; không điền ô thiếu bằng kết quả giả.

{raw_table}

| Điều kiện | Tác vụ | Check | Token | Giây | Tool calls chính | Gọi task | Trạng thái |
|---|---|---|---|---|---|---|---|
{chr(10).join(run_rows)}

Bảng sau chỉ giữ lượt hoàn tất hoặc hết ngân sách agent, loại lỗi kết nối; lưu table-usable.md. Các điều kiện có số tác vụ khác nhau nên không so trực tiếp trung bình:

{usable_table}

Đầu ra nguyên scripts/check_breakdown.py (cũng chứa lượt lỗi mạng):

```text
{breakdown}
```

Cả 6 bản ghi có skills_modified=false; baseline/subagents không nạp skill, nên đây chưa là bằng chứng freeze. submission-audit.json ghi rõ 12 bản ghi còn thiếu, hai lượt hạ tầng không hợp lệ và chưa có tag. results/archive giữ thử nghiệm môi trường và lượt lỗi; event finish được dùng tính ngân sách, tránh cộng chồng bản sao.

## 8. Phân tích

1. **Điểm học/đánh giá:** baseline code đạt 0,70, logs 0,67, data 0; trung bình học 0,456 gồm thất bại ngân sách. Cặp data với subagents đều 0. Chưa đo skills-auto/eval nên chưa kiểm chứng H1–H3, cải thiện hoặc quá khớp.
2. **Kỹ thuật/quy ước:** baseline tổng kỹ thuật 13/18, quy ước 0/9; riêng hai lượt hoàn tất 13/13 và 0/6. repo-conventions nhắm 3 lỗi E ở code, nhưng chưa chạy nên chỉ là cơ chế dự kiến. Không có bằng chứng giúp check cũ hoặc check mới của eval.
3. **Đọc/làm theo skill:** chưa có run skills-auto; không nêu một check đã được skill cải thiện. skills_read>0 sau này cần đối chiếu hành động thật và checker; số này chỉ đo đọc trong luồng chính.
4. **Chi phí:** baseline trung bình 365.170 token nếu tính cả hết ngân sách, hoặc 161.602 token trên hai lượt hoàn tất. Subagents hiện chỉ có một lượt không lỗi hạ tầng, khác tập tác vụ; trung bình raw 211.939 không là đối chứng hợp lệ. Không đánh giá lợi ích trên mỗi token của đa tác tử khi chưa có delegation. Vòng lặp data chiếm phần lớn ngân sách baseline hiện tại.
5. **Rò rỉ/quá khớp:** nguồn curator chỉ baseline learn, không dùng eval; hai skill giữ lại qua validate_skill và được đọc kiểm tra. Các tên/schema của quy ước tổ chức là phản hồi được phép học; số lượng dòng/token không chứng minh khả năng tổng quát. Bộ lọc marker không phát hiện mọi cách diễn đạt lại/Unicode, và chưa có kết quả eval để đo quá khớp.
6. **Nhiễu:** chưa có skills-auto-dev và lượt học sau freeze với cùng hash, nên không đo chênh lệch. Retry vì error không thay cho phép đo nhiễu; temperature=0 vẫn chưa bảo đảm lặp lại.

## 9. Hạn chế và tính hợp lệ

1. Thiếu 12/18 bản ghi và có hai lỗi kết nối; chưa đủ đối chứng, chưa đóng băng đúng quy trình. Không kết luận tự tiến hóa cải thiện agent.
2. Chỉ một model, ba họ nhỏ, quy ước giảng viên thiết kế; mọi kết luận chỉ có phạm vi lab. Các lượt hết ngân sách tạo nhiều check thiếu tệp từ một nguyên nhân, không là tám lỗi độc lập.
3. Mỗi điều kiện dự kiến một lượt chính thức, chưa có đo nhiễu; pacing và mạng ảnh hưởng thời gian. Tổng usage là cận dưới, token không tương đương hóa đơn.
4. Vết cung cấp giới hạn 1.500 ký tự mỗi message và chỉ chứa luồng chính; không quan sát toàn bộ suy luận hoặc công cụ bên trong worker. Callback đo token worker khi trả usage; request bị ngắt có thể không đo được.
5. Git Bash/native backend phục vụ test, không cách ly shell ở mức hệ điều hành. Số liệu cuối dùng Docker; mọi thử CMD/Git Bash/Docker trước guard bị loại khỏi phân tích chính thức. Giới hạn đường dẫn shell là quy tắc thao tác, container là cơ chế cách ly.
6. Skill hợp lệ định dạng vẫn có thể gây sai; một skill đã bị loại vì phạm vi. Bộ giữ lại chưa được kiểm chứng hành vi, nên không coi là đủ an toàn/chính xác cho mọi tác vụ.

## 10. Kết luận

Harness, ba worker, runner và curator đã cài đặt; {tests['tests'] - tests['skipped']} kiểm thử ngoại tuyến đạt. Baseline hoàn tất code với 7/10 và logs với 6/9, trong đó kỹ thuật đạt toàn bộ nhưng thiếu sáu quy ước tổ chức. Data ở hai điều kiện đều không tạo đầu ra trước giới hạn, và các vết subagents hiện tại không có delegation. Curator thật sinh ba skill, tuyển chọn còn hai nguyên bản, nhưng chưa có dữ liệu chứng minh cải thiện. Cần nguồn truy cập model để kiểm tra skill trên học, đăng ký/đóng băng rồi chạy các lượt đánh giá còn thiếu; phần này chưa hoàn tất khi API key đã gỡ.

## Phụ lục

- Trình tự thực hiện và lệnh tái lập: RUNBOOK.md; nhật ký thật: experiment-events.jsonl; tổng ngân sách: budget.json. Thử kết nối/công cụ dùng API trước khi key gỡ; lượt chốt báo cáo này chỉ chạy ngoại tuyến.
- Bằng chứng: offline-tests.xml, tour.txt, environment.txt, experiment-manifest.json, curator-run.json, skill-selection.json, analysis.json, submission-audit.json và results/<condition>/<task>/run.json + trace.md.
- Kiểm tra mã cung cấp không đổi: tests/tasks/scripts, model/tasks/grading/testing/compare và AST của hằng số/hàm cung cấp. Audit còn thiếu dữ liệu như đã nêu; kiểm thử không thay thế thực nghiệm.
- .env không được git theo dõi. Quét pattern key thông dụng và giá trị key cấu hình (nếu còn) bằng audit; không lưu hoặc in key. Key đã gỡ nên quét theo giá trị cấu hình không còn bao phủ key cũ.
- Thử thách 6c có công cụ mô phỏng guard riêng nhưng chưa chạy; không báo cáo đó là tỷ lệ jailbreak của DeepSeek. Không tạo tag freeze để che việc thiếu dev/eval.
"""
    report_path.write_text(content, encoding="utf-8")
    state = {"timestamp": datetime.now(timezone.utc).isoformat(), "mode": "offline",
             "model_api_calls_in_finalization": 0, "tests": tests, "recorded_runs": len(runs),
             "expected_runs": 18, "submission_complete": False, "audit_status": audit["status"]}
    (report_dir / "completion-status.json").write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(state, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
