"""Verify the real grader does not confuse CRLF checkout with agent edits."""
import os

import pytest
from langchain_core.messages import AIMessage

from lab.runner import run_task
from lab.tasks import get_task, hash_dir
from lab.testing import ScriptedChatModel
from lab.agent import make_backend


@pytest.mark.skipif(os.name != "nt", reason="Windows CRLF checkout regression")
def test_unchanged_windows_test_files_pass_the_supplied_checker(tmp_path):
    source = get_task("code-learn").dir / "workspace"
    before = hash_dir(source)
    record = run_task("code-learn", "baseline", results_dir=tmp_path,
                      model=ScriptedChatModel(script=[AIMessage(content="No edits.")]))
    check = next(c for c in record["checks"] if c["name"] == "tests_not_modified")
    assert check["passed"] is True
    assert hash_dir(source) == before
    assert record["error"] is None


@pytest.mark.skipif(os.name != "nt", reason="Git Bash on Windows regression")
def test_posix_python_heredoc_and_unicode_work_on_windows(tmp_path):
    backend = make_backend(tmp_path)
    result = backend.execute("python - <<'PY'\nprint('Tiếng Việt')\nPY")
    assert result.exit_code == 0
    assert "Tiếng Việt" in result.output
