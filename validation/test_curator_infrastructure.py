"""An interrupted API run must not become skill-learning evidence."""
import json

from langchain_core.messages import AIMessage

from lab.curator import curate_skills
from lab.testing import ScriptedChatModel


def test_curator_ignores_infrastructure_failure(tmp_path):
    run_dir = tmp_path / "results" / "baseline" / "data-learn"
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(json.dumps({
        "task": "data-learn", "role": "learn", "error": "RemoteProtocolError: interrupted",
        "checks": [{"name": "partial_output", "passed": False, "detail": "incomplete"}],
    }), encoding="utf-8")
    model = ScriptedChatModel(script=[AIMessage(content="must not be called")])
    assert curate_skills(tmp_path / "results", out_dir=tmp_path / "skills", model=model) == []
    assert model.calls == 0


def test_curator_can_learn_from_retained_agent_budget_failure(tmp_path):
    run_dir = tmp_path / "results" / "baseline" / "data-learn"
    run_dir.mkdir(parents=True)
    (run_dir / "run.json").write_text(json.dumps({
        "task": "data-learn", "role": "learn", "error": "GraphRecursionError: step budget exhausted",
        "checks": [{"name": "required_output", "passed": False, "detail": "Create the requested output file."}],
    }), encoding="utf-8")
    (run_dir / "trace.md").write_text("Repeated a command for an absent directory instead of producing outputs.", encoding="utf-8")
    reply = "=== SKILL: bounded-workflow ===\n---\nname: bounded-workflow\ndescription: Use when executing a multi-step task.\n---\nStop repeating failed searches and produce the required outputs.\n=== END ==="
    model = ScriptedChatModel(script=[AIMessage(content=reply)])
    paths = curate_skills(tmp_path / "results", out_dir=tmp_path / "skills", model=model)
    assert len(paths) == 1 and model.calls == 1
    assert '"agent_budget_exhausted": true' in model.prompts[0]
    assert "Create the requested output file." in model.prompts[0]
