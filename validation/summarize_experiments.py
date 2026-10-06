"""Rebuild report tables and numerical evidence from actual run records."""
from collections import Counter
import json
from pathlib import Path
import statistics
import subprocess

from lab.compare import build_table, load_runs
from lab.curator import validate_skill
from lab.tasks import ROOT, hash_skills


def summarize(records):
    rows = {}
    for condition in ("baseline", "subagents", "skills-auto"):
        for role in ("learn", "eval"):
            subset = [r for r in records if r["condition"] == condition and r["role"] == role]
            if not subset:
                continue
            checks = [c for r in subset for c in r["checks"]]
            technical = [c for c in checks if not c["name"].startswith("rule_")]
            rules = [c for c in checks if c["name"].startswith("rule_")]
            score = statistics.mean(r["score"] for r in subset)
            tokens = statistics.mean(r["tokens"]["total"] for r in subset)
            rows[f"{condition}/{role}"] = {
                "runs": len(subset), "mean_score": score, "mean_tokens": tokens,
                "mean_seconds": statistics.mean(r["seconds"] for r in subset),
                "technical_passed": sum(c["passed"] for c in technical), "technical_total": len(technical),
                "rules_passed": sum(c["passed"] for c in rules), "rules_total": len(rules),
                "score_per_1000_tokens": score / tokens * 1000 if tokens else None,
                "subagent_calls": sum(r["subagent_calls"] for r in subset),
                "runs_reading_skills": sum(r["skills_read"] > 0 for r in subset),
            }
    return rows


def main():
    frozen = subprocess.run(["git", "rev-parse", "--verify", "freeze"], cwd=ROOT,
                            capture_output=True).returncode == 0
    records = []
    for condition in ("baseline", "subagents", "skills-auto"):
        for path in sorted((ROOT / "results" / condition).glob("*/run.json")):
            # Never inspect evaluation results before the freeze protocol.
            if not frozen and path.parent.name.endswith("-eval"):
                continue
            records.append(json.loads(path.read_text(encoding="utf-8")))
    failures = [dict(task=r["task"], **c) for r in records
                if r["condition"] == "baseline" and r["role"] == "learn" and
                (not r["error"] or r["error"].startswith("GraphRecursionError:"))
                for c in r["checks"] if not c["passed"]]
    workers = {}
    for r in records:
        if r["condition"] != "subagents":
            continue
        path = ROOT / "results" / "subagents" / r["task"] / "trace.md"
        counts = Counter()
        for block in path.read_text(encoding="utf-8").split("### Tool call: task\n")[1:]:
            line = block.splitlines()[0]
            try:
                counts[json.loads(line).get("subagent_type", "unknown")] += 1
            except json.JSONDecodeError:
                counts["truncated-in-trace"] += 1
        workers[r["task"]] = dict(counts)
    skills = []
    for path in sorted((ROOT / "skills" / "auto").glob("*/SKILL.md")):
        contents = path.read_text(encoding="utf-8")
        skills.append({"name": path.parent.name, "lines": len(contents.splitlines()),
                       "validation": validate_skill(contents, path.parent.name)})
    noise = []
    for r in records:
        if r["condition"] != "skills-auto" or r["role"] != "learn":
            continue
        path = ROOT / "results" / "skills-auto-dev" / r["task"] / "run.json"
        if path.exists():
            dev = json.loads(path.read_text(encoding="utf-8"))
            noise.append({"task": r["task"], "dev_passed": dev["passed"],
                          "official_passed": r["passed"], "total": r["total"],
                          "score_delta": r["score"] - dev["score"],
                          "same_skills": r["skills_sha256"] == dev["skills_sha256"],
                          "dev_tokens": dev["tokens"]["total"], "official_tokens": r["tokens"]["total"]})
    usable = [r for r in records if not r["error"] or r["error"].startswith("GraphRecursionError:")]
    excluded = [f"{r['condition']}/{r['task']}" for r in records if r not in usable]
    evidence = {"freeze_exists": frozen, "recorded_runs": len(records),
                "expected_official_runs": 18, "usable_recorded_runs": len(usable),
                "excluded_infrastructure_runs": excluded,
                "official_total_tokens": sum(r["tokens"]["total"] for r in records),
                "errors": [r["task"] for r in records if r["error"]],
                "modified_skills": [r["task"] for r in records if r["skills_modified"]],
                "summary": summarize(usable), "raw_summary": summarize(records), "learning_failures": failures,
                "worker_calls_from_trace": workers, "skills": skills,
                "skills_sha256": hash_skills(ROOT / "skills" / "auto"), "noise": noise}
    (ROOT / "report" / "analysis.json").write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (ROOT / "report" / "table.md").write_text(build_table(records) + "\n", encoding="utf-8")
    (ROOT / "report" / "table-usable.md").write_text(build_table(usable) + "\n", encoding="utf-8")
    print(json.dumps(evidence, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
