"""Write the completed report from real frozen experiments; never call a model."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from lab.tasks import ROOT, hash_skills


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True,
                          text=True, encoding="utf-8").stdout.strip()


def run_python(script):
    return subprocess.run([str(ROOT / ".venv" / "Scripts" / "python.exe"), "-X", "utf8", script],
                          cwd=ROOT, check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()


def main():
    report_dir = ROOT / "report"
    old = (report_dir / "REPORT.md").read_text(encoding="utf-8")
    familiarization = old.split("## 3. Làm quen Deep Agents (Phần 0.3)\n", 1)[1].split("## 4.", 1)[0].strip()
    hypotheses = "\n".join(line for line in (report_dir / "hypotheses.md").read_text(encoding="utf-8").splitlines() if line.startswith("- H"))
    runs = [read(path) for condition in ("baseline", "subagents", "skills-auto")
            for path in sorted((ROOT / "results" / condition).glob("*/run.json"))]
    assert len(runs) == 18, "Complete all 18 official runs before writing the final report"
    assert all(not r["error"] or r["error"].startswith("GraphRecursionError:") for r in runs), "Resolve infrastructure errors first"
    freeze_check = run_python("scripts/verify_freeze.py")
    assert "6 runs" in freeze_check and freeze_check.endswith("OK")
    analysis = read(report_dir / "analysis.json")
    cell = {(r["condition"], r["task"]): r for r in runs}
    def get(condition, family, role):
        return cell[(condition, f"{family}-{role}")]
    def fmt(value):
        return f"{value:.3f}"
    def stats(condition, role):
        return analysis["summary"][f"{condition}/{role}"]
    summaries = []
    for condition in ("baseline", "subagents", "skills-auto"):
        for role in ("learn", "eval"):
            s = stats(condition, role)
            summaries.append(f"| {condition} | {role} | {fmt(s['mean_score'])} | {s['technical_passed']}/{s['technical_total']} | {s['rules_passed']}/{s['rules_total']} | {s['mean_tokens']:,.0f} | {s['mean_seconds']:.1f} | {s['subagent_calls']} |")
    detail_rows = []
    errors = []
    for r in runs:
        state = "Hết ngân sách 100 bước" if r["error"] else "Hoàn tất"
        if r["error"]:
            errors.append(f"{r['condition']}/{r['task']}")
        detail_rows.append(f"| {r['condition']} | {r['task']} | {r['passed']}/{r['total']} | {r['tokens']['total']:,} | {r['seconds']} | {r['tool_calls']} | {r['subagent_calls']} | {r['skills_read']} | {state} |")
    failures = []
    taxonomy = Counter()
    for failure in analysis["learning_failures"]:
        group = "G — hết ngân sách, thiếu đầu ra" if failure["task"] == "data-learn" else "E — quy ước tổ chức"
        taxonomy[group.split(" ")[0]] += 1
        detail = "FileNotFoundError: answer.json chưa được tạo" if "FileNotFoundError" in failure["detail"] else failure["detail"]
        failures.append(f"| {failure['task']} | {failure['name']} | {group} | {detail.replace('|', '/')} |")
    # Distinguish organization rules reused from learn from newly introduced rules.
    rule_rows = []
    new_rules = []
    for family in ("code", "data", "logs"):
        known = {c["name"] for c in get("baseline", family, "learn")["checks"] if c["name"].startswith("rule_")}
        for c in get("baseline", family, "eval")["checks"]:
            if not c["name"].startswith("rule_"):
                continue
            kind = "Đã có trên learn" if c["name"] in known else "Mới trên eval"
            if c["name"] not in known:
                new_rules.append((family, c["name"]))
            values = []
            for condition in ("baseline", "subagents", "skills-auto"):
                check = next(x for x in get(condition, family, "eval")["checks"] if x["name"] == c["name"])
                values.append("Đạt" if check["passed"] else "Không đạt")
            rule_rows.append(f"| {family} | {c['name']} | {kind} | {' | '.join(values)} |")
    noise_rows = [f"| {r['task']} | {r['dev_passed']}/{r['total']} | {r['official_passed']}/{r['total']} | {r['score_delta']:+.3f} | {r['dev_tokens']:,} | {r['official_tokens']:,} | {'Có' if r['same_skills'] else 'Không'} |" for r in analysis["noise"]]
    assert len(noise_rows) == 3 and all(r["same_skills"] for r in analysis["noise"])
    noise_note = ("Cả ba cặp đều có delta score bằng 0; chưa quan sát biến động điểm, nhưng token và thời gian khác nhau. Điều này không chứng minh phương sai bằng 0." if all(r["score_delta"] == 0 for r in analysis["noise"]) else "Các delta score trong bảng là dao động quan sát được trên cùng bộ skill.")
    events = [json.loads(line) for line in (report_dir / "experiment-events.jsonl").read_text(encoding="utf-8").splitlines() if line]
    finishes = [e for e in events if e["event"] == "finish"]
    curator_history = read(report_dir / "curator-history.json")
    probe_tokens = sum(p["usage"]["total_tokens"] for p in read(report_dir / "model-tool-probe.json"))
    resume_tokens = read(report_dir / "resume-probe.json")["tokens"]["total"]
    budget = {"finished_task_attempts": len(finishes), "finished_task_tokens": sum(e["tokens"] for e in finishes),
              "curator_calls": len(curator_history), "curator_tokens": sum(r["tokens"]["total"] for r in curator_history),
              "tool_probe_tokens": probe_tokens, "resume_probe_tokens": resume_tokens,
              "official_task_tokens": sum(r["tokens"]["total"] for r in runs),
              "token_total_is_lower_bound": True,
              "unmeasured": ["small original API connection probe", "requests interrupted before usage returned", "older runs outside event history"]}
    budget["measured_tokens_lower_bound"] = budget["finished_task_tokens"] + budget["curator_tokens"] + probe_tokens + resume_tokens
    (report_dir / "budget.json").write_text(json.dumps(budget, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    suites = ET.parse(report_dir / "offline-tests.xml").getroot().findall("testsuite")
    test_count = sum(int(s.get("tests", 0)) - int(s.get("skipped", 0)) for s in suites)
    assert not any(int(s.get("failures", 0)) + int(s.get("errors", 0)) for s in suites)
    freeze_commit = git("rev-parse", "freeze^{commit}")
    hyp_commit = git("log", "freeze", "--format=%H", "--grep=^hypotheses").splitlines()[0]
    # The predictions in the sealed registration and final report must agree.
    registered = git("show", f"{hyp_commit}:report/REPORT.md")
    assert all(line in registered for line in hypotheses.splitlines())
    table = (report_dir / "table.md").read_text(encoding="utf-8").strip()
    breakdown = "\n".join(line.rstrip() for line in run_python("scripts/check_breakdown.py").splitlines())
    (report_dir / "check-breakdown.txt").write_text(breakdown + "\n", encoding="utf-8")
    learn_gain = stats("skills-auto", "learn")["mean_score"] - stats("baseline", "learn")["mean_score"]
    eval_gain = stats("skills-auto", "eval")["mean_score"] - stats("baseline", "eval")["mean_score"]
    sub_eval = stats("subagents", "eval")
    base_eval = stats("baseline", "eval")
    skill_eval = stats("skills-auto", "eval")
    sub_token_ratio = sub_eval["mean_tokens"] / base_eval["mean_tokens"]
    h1_tech = sub_eval["technical_passed"] / sub_eval["technical_total"] >= base_eval["technical_passed"] / base_eval["technical_total"]
    h1_cost = sub_token_ratio >= 1.20
    highest = skill_eval["mean_score"] >= max(base_eval["mean_score"], sub_eval["mean_score"])
    h1 = "Phù hợp cả hai dự đoán" if h1_tech and h1_cost else "Không phù hợp đầy đủ"
    h2 = "Phù hợp" if highest and eval_gain >= .15 else "Không phù hợp đầy đủ"
    h3 = "Phù hợp về số điểm quan sát" if learn_gain > eval_gain else "Không phù hợp về số điểm quan sát"
    hypothesis_results = {"H1": {"technical_at_least_baseline": h1_tech, "token_ratio": sub_token_ratio,
                                  "token_increase_at_least_20_percent": h1_cost},
                          "H2": {"skills_highest_eval": highest, "eval_gain": eval_gain,
                                  "gain_at_least_0_15": eval_gain >= .15},
                          "H3": {"learn_gain": learn_gain, "eval_gain": eval_gain,
                                  "learn_gain_greater": learn_gain > eval_gain},
                          "limitation": "One run per task; observational comparison, not statistical confirmation."}
    (report_dir / "hypothesis-results.json").write_text(json.dumps(hypothesis_results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    rule_new_summary = []
    for family, name in new_rules:
        passed = next(c["passed"] for c in get("skills-auto", family, "eval")["checks"] if c["name"] == name)
        rule_new_summary.append(f"{family}/{name}: {'đạt' if passed else 'không đạt'}")
    data_failures = []
    for role in ("learn", "eval"):
        for c in get("skills-auto", "data", role)["checks"]:
            if not c["passed"]:
                data_failures.append(f"data-{role}/{c['name']}")
    workers = json.dumps(analysis["worker_calls_from_trace"], ensure_ascii=False)
    control = read(report_dir / "redteam" / "results.json") if (report_dir / "redteam" / "results.json").exists() else None
    guard_text = (f"Thử bộ lọc bằng 6 phản hồi tổng hợp: guard gốc nhận {control['original_malicious_accepted']}/5 phản hồi độc hại; nhánh chuẩn hóa Unicode nhận {control['guard_malicious_accepted']}/5. Ba skill đóng băng hợp lệ ở cả hai guard. Không dùng guard thử vào thí nghiệm chính và không đo tỷ lệ jailbreak của DeepSeek; đây là phép thử ngoại tuyến ranh giới validator." if control else "Chưa thực hiện thử thách mở rộng; không dùng kết quả tổng hợp thay cho dữ liệu API.")
    content = f"""# Báo cáo Lab: Self-evolving Agentic

Trạng thái: **đã hoàn tất 18/18 lượt chính thức và 3 lượt skill-dev, đăng ký H1–H3 trước đánh giá, đóng băng 3 skill tự sinh và kiểm tra freeze**. Có {len(errors)} lượt agent chạm giới hạn 100 bước, được giữ nguyên như kết quả âm có vết và chấm workspace dở dang; không trình bày là thành công. Các lượt lỗi mạng/môi trường trước đó nằm trong archive, không gộp vào bảng chính thức. Báo cáo dùng kết quả API thật; kiểm thử ngoại tuyến được ghi riêng.

## 1. Thông tin nhóm và cấu hình

| Họ tên | Mã sinh viên | Phần đóng góp |
|---|---|---|
| Trần Anh Quân | 2A202602598 | 100% |

- Alias: LAB_MODEL=deepseek:deepseek-chat; temperature=0; recursion_limit=100. Callback ở lượt nối lại API báo deepseek-flash. Lượt đánh giá của cả ba điều kiện dùng cùng phiên cấu hình sau sửa retry SDK; các bản ghi học cũ không có identity trả về nên chỉ xác nhận alias cấu hình.
- Host Windows 10/Python 3.11.9, Deep Agents 0.7.21. Shell tác vụ Docker Linux/Python 3.11.17 với image lab-agent-sandbox:py311; định danh image và phiên bản ở experiment-manifest.json/environment.txt.
- Container chỉ mount sandbox, tắt mạng, root filesystem chỉ đọc, không nhận API key. Công cụ tệp và shell dùng cùng bản sao; shell kiểm tra đường dẫn tương đối. Chuẩn hóa LF trên bản sao Python trước chạy để phù hợp checker Windows; mã tác vụ gốc và byte skill được giữ nguyên.
- 2 worker/tác vụ độc lập mỗi batch, pacing 12 RPM mỗi tiến trình dùng chung main/subagent. Các batch chính thức chạy song song nên tổng trần lý thuyết 36 RPM. HTTP 429/503 chờ 30 giây, tối đa 3 retry; client SDK sync/async không retry ngầm. Lượt hạ tầng được chạy lại tối đa 1 lần, không retry do hết ngân sách hoặc điểm thấp.
- **{test_count} kiểm thử đạt**, gồm 29 test cung cấp, test pacing/retry thật qua MockTransport và 4 test Docker. MockTransport không gọi API và không được tính vào điểm thí nghiệm.
- Đã ghi {len(finishes)} lượt task finish qua các giai đoạn, {len(curator_history)} lần curator thật, 18 lượt task chính thức + 3 dev. Token chính thức: **{budget['official_task_tokens']:,}**; tổng đã đo kể cả thử nghiệm/retry/curator/probe ít nhất **{budget['measured_tokens_lower_bound']:,}** input+output. Chưa bao gồm usage không trả về khi ngắt và lịch sử cũ ngoài nhật ký; không quy đổi tiền.
- Commit hypotheses: {hyp_commit}; freeze: {freeze_commit}, thời điểm {git('log', '-1', '--format=%cI', 'freeze')}. Hash skill: {hash_skills(ROOT / 'skills' / 'auto')}. Kiểm tra cung cấp: **{freeze_check}**.

## 2. Giả thuyết (commit TRƯỚC tag freeze, Phần 4.0)

Giữ nguyên câu chữ từ hypotheses.md và commit đăng ký; không sửa dự đoán sau khi thấy điểm eval.

{hypotheses}

## 3. Làm quen Deep Agents (Phần 0.3)

{familiarization}

## 4. Đường cơ sở và phân loại lỗi (Phần 2.2)

Chỉ dùng baseline learn trong cấu hình Docker cuối. Lỗi FileNotFoundError ở check là hệ quả thiếu đầu ra khi agent hết bước, không đủ để suy ra sai thuật toán hoặc đã biết/vi phạm schema. Phản hồi có RULE cụ thể được dùng học quy ước; feedback thiếu answer.json không tiết lộ meta đầy đủ.

| Tác vụ | Check thất bại | Nhóm lỗi | Bằng chứng detail/vết |
|---|---|---|---|
{chr(10).join(failures)}

Có {taxonomy['E']} lỗi E trực tiếp trên code/logs và {taxonomy['G']} check thất bại dây chuyền trên data (G). Riêng hai lượt baseline hoàn tất đạt kỹ thuật **13/13**, quy ước **0/6**; cả sáu lỗi đều là E. Code đạt bảo toàn test, docstring, giá, half-up và CSV; logs đạt UTC, exception/repeat/thống kê. Không có bằng chứng A–D ở hai lượt này; không suy rộng sang data, không đếm tám check thiếu đầu ra là tám nguyên nhân độc lập. Vết data lặp chẩn đoán dòng trùng thay vì ghi answer.json/clean.csv trước giới hạn; quy trình giới hạn chẩn đoán và kiểm chứng tệp là ứng viên cải tiến.

## 5. Điều kiện subagents (Phần 2.3)

| Worker | Vai trò | Lý do thiết kế |
|---|---|---|
| explorer | Đọc đặc tả/schema/dữ liệu, không sửa tệp | Giảm bỏ sót ràng buộc |
| implementer | Sửa/xử lý và chạy kiểm chứng | Tập trung thực hiện thay đổi |
| reviewer | Kiểm tra độc lập, không sửa tệp | Đối chiếu đầu ra/trường hợp biên |

Các worker nhận PATHS_NOTE qua system prompt và chỉ thấy ngữ cảnh giao việc; dùng chung tệp sandbox. Explorer/reviewer được yêu cầu chỉ đọc bằng prompt, chưa khóa quyền ghi bằng tools. Trace chỉ ghi luồng chính và báo cáo worker; khi arguments bị cắt, không suy đoán loại worker. Số gọi task của từng lượt ở mục 7; worker xác định được từ vết: {workers}.

Ở code-learn, coordinator đã giao việc một lần; vết ghi mục tiêu sửa package theo docstring, đường dẫn workspace và cấm sửa tests, cùng mã nguồn. Coordinator đọc lại pricing/export/report và chạy test/kiểm chứng độc lập trước kết luận. Arguments dài bị cắt 1.500 ký tự nên không chứng minh toàn bộ quy tắc đã được truyền. Ba quy ước tổ chức vẫn không đạt: chúng chưa có trong đề/context của worker. Lượt logs-learn lặp tìm skills/ không tồn tại, hết bước và không delegation; là kết quả âm thực tế, không phải mô hình giả.

## 6. Self-evolving: skill do curator sinh (Phần 3)

Curator chỉ dùng baseline role=learn, failed-check detail và tối đa 6.000 ký tự cuối vết; bỏ lỗi mạng, giữ hết ngân sách với cờ agent_budget_exhausted. Đã gọi thật 2 lần (1 rerun trong mức GUIDE cho phép), dùng {budget['curator_tokens']:,} token. Lần đầu sinh 3 skill hợp lệ định dạng, nhưng structured-output-rules trộn schema log vào JSON dữ liệu và lọc missing quá sớm; đã loại và lưu nguyên bản. Lần hai sinh bộ tách miền, thay bộ cũ và giữ nguyên byte từ output curator. Provenance: curator-history.json, curator-attempt-2/skills, skill-selection.json. Không chỉnh tay hoặc tái sinh sau freeze.

| Skill | Mức tổng quát | Đúng/sai và phạm vi | Độ dài/description |
|---|---|---|---|
| python-package-fix | Sửa Python theo docstring, kiểm tra source và quy ước tổ chức | Type hints, tên regression file, changelog khớp feedback code; ít nhất 3 vẫn là quy ước lab, không phải quy tắc mọi repo | 12 dòng; kích hoạt khi sửa package Python |
| tabular-data-cleanup | Kiểm tra/dedup/canonicalize/UTC/money, tạo và đọc lại artifact | Quy trình hữu ích nhưng không có meta schema cụ thể vì baseline chưa tạo answer; yêu cầu money cents có thể bị chỉ áp vào CSV; tệp clean phải lọc unknown theo feedback | 14 dòng; kích hoạt CSV/tabular aggregation |
| log-triage | Parse entries/traceback/repeat/UTC, canonical service/sort/schema | Khớp feedback logs; không áp schema log sang JSON khác. Không bao phủ mọi quy ước mới của eval | 15 dòng; kích hoạt JSON triage log |

Trước freeze, dev đạt code 10/10, data 5/8, logs 9/9; skills_read lần lượt 1/3/1 và skills_modified=false. Code thêm hints/regression/changelog, logs chuẩn hóa các quy ước học. Data đọc cả ba skill nhưng answer vẫn dùng tiền float, tự thêm schema_version/generated_by không đúng meta, và CSV chứa dòng unknown có amount trống; ba rule_ không đạt. Đọc skill không đồng nghĩa làm theo hoặc biết schema chưa có trong nguồn học. Giữ nguyên kết quả dev, không dùng phản hồi eval để chỉnh skill.

## 7. Kết quả so sánh (Phần 4.3, 4.4)

Bảng do nguyên hàm lab.compare sinh từ đủ 18 record. GraphRecursionError là kết quả workspace trong giới hạn 100 bước; các mean dưới đây gồm những lượt đó, không diễn giải là tất cả agent đã hoàn tất.

{table}

| Điều kiện | Role | Mean score | Kỹ thuật | Quy ước | Mean token | Mean giây | Gọi task |
|---|---|---|---|---|---|---|---|
{chr(10).join(summaries)}

| Điều kiện | Tác vụ | Check | Token | Giây | Tool calls chính | Gọi task | Đọc skill | Trạng thái |
|---|---|---|---|---|---|---|---|---|
{chr(10).join(detail_rows)}

Đầu ra công cụ cung cấp:

```text
{breakdown}
```

Các lượt có error: {', '.join(errors) or 'không có'}. Tất cả 18 lượt có trace/usage và skills_modified=false; không còn lượt lỗi mạng trong bảng chính thức. Lượt mạng/môi trường bị thay thế được giữ archive; không chọn theo điểm. Kiểm tra freeze đối chiếu đủ 6 lượt skills-auto, đúng hash và timestamp sau tag. Một số lượt học cũ trước sửa SDK nên tính chi phí học cần xét hạn chế ở mục 9.

## 8. Phân tích

1. **Học và đánh giá:** skills-auto tăng mean learn **{learn_gain:+.3f}**, mean eval **{eval_gain:+.3f}** so với baseline. H1: {h1}; kỹ thuật subagents eval {sub_eval['technical_passed']}/{sub_eval['technical_total']} so với baseline {base_eval['technical_passed']}/{base_eval['technical_total']}, token ratio {sub_token_ratio:.2f} lần. H2: {h2}; skills-auto {'đạt' if highest else 'không đạt'} điểm eval cao nhất, chênh lệch {eval_gain:+.3f} so với ngưỡng dự đoán 0,15. H3: {h3}; gain learn {learn_gain:+.3f} và eval {eval_gain:+.3f}. Đây là đối chiếu dự đoán trên mẫu nhỏ, không phải kiểm định thống kê hoặc chứng minh quan hệ nhân quả.

2. **Kỹ thuật/quy ước:** so sánh tách check ở bảng dưới. Nhóm học lại quy ước giúp kiểm tra cơ chế self-evolving, nhóm mới cho thấy giới hạn tổng quát. Check mới của skills-auto: {'; '.join(rule_new_summary)}. Không thể suy ra skill biết quy ước mới chỉ vì description phù hợp.

| Họ | Check eval | Loại | baseline | subagents | skills-auto |
|---|---|---|---|---|---|
{chr(10).join(rule_rows)}

3. **Đọc và làm theo:** code là ví dụ được hỗ trợ: baseline thiếu rule_type_hints/regression/changelog, dev đọc python-package-fix rồi thực sự thêm các artifact; ba rule đạt. Logs dev đọc log-triage và đạt chuẩn service/sort/schema. Data là ví dụ không đủ: đọc cả ba skill nhưng tiền answer vẫn float, meta bị đoán và clean CSV gồm unknown. Các check data của skills-auto còn thất bại: {', '.join(data_failures) or 'không có'}. Chi tiết official và checker là bằng chứng quyết định; skills_read chỉ đếm main-thread read_file, không quan sát bên trong worker.

4. **Chi phí:** mean token eval lần lượt baseline {base_eval['mean_tokens']:,.0f}, subagents {sub_eval['mean_tokens']:,.0f}, skills-auto {skill_eval['mean_tokens']:,.0f}. Điểm/1.000 token tương ứng {base_eval['score_per_1000_tokens']:.6f}, {sub_eval['score_per_1000_tokens']:.6f}, {skill_eval['score_per_1000_tokens']:.6f}. Tỷ lệ này tính cả lượt hết ngân sách; chưa đủ để kết luận chi phí đa tác tử đáng giá ở mọi tác vụ. Delegation cần gắn với check và hành động, không chỉ tên condition. Token gồm main/worker, tool_calls chỉ luồng chính, thời gian gồm pacing/retry/Docker. Không quy đổi token thành tiền khi thiếu hóa đơn và phần cached input.

5. **Rò rỉ/quá khớp:** nguồn curator chỉ baseline learn, không eval; hai lần tuyển chọn diễn ra trước tag, không sửa byte sau freeze. Validator không thấy marker eval trong 3 skill; giữ schema/filenames quy ước được feedback cho phép, không giữ đáp án học. Gain học lớn hơn eval nếu có chỉ là dấu hiệu cần đối chiếu nhiễu, độ khó và thay đổi router, không tự chứng minh quá khớp. Bộ lọc marker không chặn mọi Unicode/diễn đạt lại.

6. **Nhiễu cùng skill:** dev và official learn có cùng hash; so sánh từng tác vụ dưới đây. {noise_note} Hai lượt mỗi tác vụ chỉ là ước lượng thô; chênh lệch gần mức dao động này cần thận trọng, và temperature=0 không bảo đảm lặp lại hoàn toàn.

| Tác vụ | Dev | Official | Delta score | Token dev | Token official | Cùng hash |
|---|---|---|---|---|---|---|
{chr(10).join(noise_rows)}

## 9. Hạn chế và tính hợp lệ

1. Chỉ ba tác vụ mỗi role, một lượt chính thức mỗi cấu hình và hai lượt cùng skill trên learn. Một vòng lặp có thể làm lệch mean; không có khoảng tin cậy/kiểm định để suy rộng.
2. Lượt baseline/subagents học cũ trước nối lại API dùng cùng alias nhưng chưa lưu model trả về; callback mới báo deepseek-flash. Đã sửa SDK retries giữa hai giai đoạn; vì vậy gain/chi phí học có nhiễu cấu hình và thời điểm. Toàn bộ eval dùng phiên sau sửa, nên phần đối chứng eval đồng nhất hơn.
3. House rules do giảng viên thiết kế và chỉ một alias model. Đạt quy ước học không tự chứng minh năng lực suy luận tổng quát; metadata chưa được feedback khi answer thiếu là giới hạn quan trọng của curator.
4. Các GraphRecursionError có partial workspace chấm được nhưng không phải lượt thành công; nhiều check thiếu tệp cùng một nguyên nhân. Không nhầm giảm token của lượt thất bại với tiết kiệm để hoàn thành tác vụ.
5. Trace cung cấp cắt 1.500 ký tự mỗi message, không có worker internals. Không xác minh toàn bộ delegation dài hoặc mọi bước suy luận; usage callback có thể thiếu request bị ngắt trước trả số liệu.
6. Shell native/Git Bash không cách ly ở mức OS; chỉ kết quả Docker cuối được đưa vào so sánh. Giới hạn path thao tác và container không bảo đảm chống mọi mã độc, nhưng test chứng minh không chuyển key, mount giới hạn và mạng tắt trong cấu hình này.
7. {guard_text}

## 10. Kết luận

Đã hoàn tất 18 lượt chính thức, 3 dev và {test_count} kiểm thử với freeze xác minh đủ 6 lượt skills-auto. Skills-auto có mean eval {skill_eval['mean_score']:.3f}, so với baseline {base_eval['mean_score']:.3f} và subagents {sub_eval['mean_score']:.3f}; các rule học lại ở code/logs cho thấy cơ chế tuyển chọn skill hoạt động trong lab. Data và các quy ước mới còn giới hạn như checker/vết ở mục 8, nên không kết luận skill luôn đúng hoặc đa tác tử luôn tốt hơn. Giữ nguyên kết quả hết ngân sách và dao động dev/official thay vì chạy lại để nâng điểm. Cải tiến tiếp theo là đo lặp thêm trên cùng snapshot model và kiểm chứng việc áp dụng quy tắc theo từng artifact trước khi tạo một bộ skill mới trong thí nghiệm riêng.

## Phụ lục

- Lệnh/thứ tự: RUNBOOK.md. Nhật ký thật: experiment-events.jsonl; ngân sách: budget.json. Curator history và selection giữ provenance đầu ra tự động.
- Báo cáo đăng ký trước: git show {hyp_commit}:report/REPORT.md; H1–H3 final được so khớp nguyên văn bằng write_final_report.py. Không viết lại giả thuyết sau eval.
- Dữ liệu dev giữ ở results/skills-auto-dev; official ở results/<condition>/<task>. results-dev là bản làm việc ban đầu, không gộp trùng vào bảng/chi phí.
- Windows chạy scripts/verify_freeze.py bằng Python -X utf8 để đọc báo cáo tiếng Việt từ Git; không sửa script cung cấp. Mã tests/tasks/scripts/model/tasks/grading/testing/compare và AST hằng số/hàm cung cấp được audit đối chiếu gốc d982034.
- Kiểm tra cuối bằng submission-audit.json, offline-tests.xml và completion-status.json. .env git-ignored; quét key cấu hình/pattern trước commit, không lưu key vào artifact.
"""
    (report_dir / "REPORT.md").write_text(content, encoding="utf-8")
    print("Wrote final report from 18 real records; sealed H1-H3 unchanged.")


if __name__ == "__main__":
    main()
