"""Audit submission completeness, secrets, immutable supplied code and freeze."""
import ast
import json
import re
from pathlib import Path
import subprocess

from dotenv import dotenv_values
from lab.curator import validate_skill
from lab.tasks import ROOT, hash_skills

ORIGINAL = "d982034"


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True)


def selected_nodes(source, names):
    selected = {}
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names:
            selected[node.name] = ast.dump(node)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in names:
                    selected[target.id] = ast.dump(node)
    return selected


def main():
    problems = []
    unchanged = ["tests", "tasks", "scripts", "src/lab/model.py", "src/lab/tasks.py",
                 "src/lab/grading.py", "src/lab/testing.py", "src/lab/compare.py"]
    changed = git("diff", "--name-only", ORIGINAL, "--", *unchanged).stdout.decode().splitlines()
    if changed:
        problems.append(f"Supplied files changed: {changed}")
    for file, names in {
        "src/lab/agent.py": {"PATHS_NOTE", "BASE_PROMPT", "SKILLS_NOTE", "SUBAGENTS_NOTE"},
        "src/lab/runner.py": {"render_trace", "main", "CONDITIONS"},
        "src/lab/curator.py": {"validate_skill", "parse_skill_blocks", "SAFE_NAME"},
    }.items():
        original = git("show", f"{ORIGINAL}:{file}").stdout.decode("utf-8")
        current = (ROOT / file).read_text(encoding="utf-8")
        if selected_nodes(original, names) != selected_nodes(current, names):
            problems.append(f"Supplied declarations changed: {file}")
    key_values = [v for k, v in dotenv_values(ROOT / ".env").items()
                  if k.endswith("_KEY") and v and len(v) >= 12]
    files = git("ls-files", "--cached", "--others", "--exclude-standard", "-z").stdout.split(b"\0")
    for name in files:
        if not name:
            continue
        path = ROOT / name.decode("utf-8")
        if path.is_file() and any(key.encode() in path.read_bytes() for key in key_values):
            problems.append(f"Configured secret found in {path.relative_to(ROOT)}")
        if path.is_file() and re.search(rb"\bsk-[A-Za-z0-9_-]{20,}\b", path.read_bytes()):
            problems.append(f"Potential API secret found in {path.relative_to(ROOT)}")
    if git("ls-files", ".env").stdout.strip():
        problems.append(".env is tracked")
    expected = {f"{family}-{role}" for family in ("code", "data", "logs") for role in ("learn", "eval")}
    tokens = 0
    recorded_runs = 0
    frozen = hash_skills(ROOT / "skills" / "auto")
    for condition in ("baseline", "subagents", "skills-auto"):
        found = set()
        for path in (ROOT / "results" / condition).glob("*/run.json"):
            r = json.loads(path.read_text(encoding="utf-8"))
            recorded_runs += 1
            found.add(r["task"])
            tokens += r["tokens"]["total"]
            infrastructure_error = r["error"] and not r["error"].startswith("GraphRecursionError:")
            if infrastructure_error or r["skills_modified"] or not r["total"] or r["tokens"]["total"] <= 0:
                problems.append(f"Invalid run: {condition}/{r['task']}")
            if not path.with_name("trace.md").is_file() or not path.with_name("trace.md").stat().st_size:
                problems.append(f"Missing trace: {condition}/{r['task']}")
            if condition == "skills-auto" and r["skills_sha256"] != frozen:
                problems.append(f"Wrong skills: {r['task']}")
        if found != expected:
            problems.append(f"Missing tasks in {condition}: {sorted(expected - found)}")
    skills = list((ROOT / "skills" / "auto").glob("*/SKILL.md"))
    if not skills:
        problems.append("No generated skills")
    for path in skills:
        if validate_skill(path.read_text(encoding="utf-8"), path.parent.name):
            problems.append(f"Invalid skill: {path.parent.name}")
    freeze = subprocess.run([".venv/Scripts/python.exe", "scripts/verify_freeze.py"], cwd=ROOT,
                            capture_output=True, text=True)
    if freeze.returncode:
        problems.append(freeze.stdout.strip())
    result = {"expected_official_runs": 18, "recorded_runs": recorded_runs,
              "generated_skills": len(skills), "recorded_tokens": tokens,
              "original_files_unchanged": not changed, "configured_secret_scan": "passed" if not
              any("secret" in p or ".env" in p for p in problems) else "failed",
              "configured_keys_available_for_scan": len(key_values),
              "generic_api_key_pattern_scan": "passed" if not any("secret" in p for p in problems) else "failed",
              "freeze_check": freeze.stdout.strip(), "problems": problems,
              "status": "OK" if not problems else "FAIL"}
    (ROOT / "report" / "submission-audit.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(bool(problems))


if __name__ == "__main__":
    main()
