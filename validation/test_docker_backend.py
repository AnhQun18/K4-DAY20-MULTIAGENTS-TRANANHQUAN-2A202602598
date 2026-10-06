"""Integration checks; enable with LAB_TEST_DOCKER=1 after building the image."""
import json
import os

import pytest
from lab.agent import make_backend

pytestmark = pytest.mark.skipif(os.getenv("LAB_TEST_DOCKER") != "1",
                               reason="Opt-in Docker integration tests")


@pytest.fixture
def backend(tmp_path, monkeypatch):
    monkeypatch.setenv("LAB_SHELL_BACKEND", "docker")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "private-test-sentinel")
    return make_backend(tmp_path)


def test_shell_and_file_tools_share_only_the_sandbox(backend, tmp_path):
    (tmp_path / "workspace").mkdir()
    (tmp_path / "workspace" / "input.txt").write_text("Tiếng Việt", encoding="utf-8")
    result = backend.execute("python - <<'PY'\nfrom pathlib import Path\np=Path('workspace/input.txt')\np.with_name('output.txt').write_text(p.read_text(),encoding='utf-8')\nprint(p.read_text())\nPY")
    assert result.exit_code == 0
    assert "Tiếng Việt" in result.output
    assert (tmp_path / "workspace" / "output.txt").read_text(encoding="utf-8") == "Tiếng Việt"


def test_host_secrets_and_repository_are_not_visible(backend):
    result = backend.execute("python - <<'PY'\nimport os,json\nprint(json.dumps({'key':os.getenv('DEEPSEEK_API_KEY'),'host_mount':os.path.exists('/c/Users/admin/Documents/Lab')}))\nPY")
    assert result.exit_code == 0
    assert json.loads(result.output.strip()) == {"key": None, "host_mount": False}


def test_root_is_read_only_and_external_network_is_disabled(backend):
    result = backend.execute("python - <<'PY'\nimport socket\ntry:\n    open('/outside-probe','w')\n    raise AssertionError('writable root')\nexcept OSError:\n    pass\ntry:\n    socket.create_connection(('1.1.1.1',443),timeout=1)\n    raise AssertionError('external network enabled')\nexcept OSError:\n    print('isolated')\nPY")
    assert result.exit_code == 0
    assert "isolated" in result.output


def test_shell_rejects_explicit_external_path_exploration(backend):
    for command in ("ls /", "ls /usr/local", "cat ../.env", "find . -name '*.md'"):
        result = backend.execute(command)
        assert result.exit_code == 1
        assert result.output.startswith("Error:")
