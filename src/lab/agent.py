"""GUIDE Phần 1 - Dựng tác tử (agent) bằng Deep Agents.   >>> SINH VIÊN CÀI ĐẶT make_backend VÀ build_agent <<<

Pseudo-code: guides/pseudocode/01_agent.md
Kiểm tra:    pytest tests/test_02_agent.py
"""
from pathlib import Path
import os
import sys

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from .model import make_model
from .subagents import get_subagents
from .rate_control import control_model

# TODO 1: import các thành phần cần dùng, ví dụ:
#   from deepagents import create_deep_agent
#   from deepagents.backends import LocalShellBackend
#   from .model import make_model
#   from .subagents import get_subagents

# ---- CÓ SẴN, KHÔNG SỬA: system prompt dùng chung cho mọi sinh viên (để đường cơ sở so sánh được) ----
PATHS_NOTE = (
    "PATHS: every path is relative to the sandbox root and never starts with '/'. "
    "The task files are in the folder workspace/ (for example workspace/app.log). "
    "Use exactly this relative form both in the file tools and in the shell (execute); "
    "the shell starts in the sandbox root. "
)
BASE_PROMPT = (
    "You are an engineering assistant working in a sandbox. "
    + PATHS_NOTE
    + "Use the shell to run Python and tests. "
    "When you are done, reply with a short summary that mentions only files you really created or changed."
)
SKILLS_NOTE = (
    " Skills are in the folder skills/ (one sub-folder per skill with a SKILL.md). "
    "As your FIRST action, read the SKILL.md of every skill whose description could apply to the task, "
    "then follow them. Never modify skills/."
)
SUBAGENTS_NOTE = (
    " You have specialised subagents (see the description of the task tool). "
    "For anything beyond a trivial step, delegate to a suitable subagent and put ALL the task rules and file paths "
    "in the delegation message, because a subagent sees only what you send. "
    "Check what a subagent returns before you rely on it."
)
# --------------------------------------------------------------------------------------------------


def make_backend(sandbox: Path):
    """Tạo backend (môi trường thực thi) cho tác tử.

    Yêu cầu:
      - Thư mục gốc (root_dir) là `sandbox`; đường dẫn tương đối `workspace/...` và `skills/...`
        phải dùng được ở CẢ công cụ tệp lẫn shell (shell chạy với thư mục làm việc = `sandbox`).
      - Tác tử chạy được lệnh shell và gọi được `python` (cần đặt PATH).
      - KHÔNG chuyển biến môi trường của bạn vào shell của tác tử (khóa API không được lộ).
    """
    sandbox = Path(sandbox).resolve()
    import re
    import shlex

    def path_violation(command):
        # Enforce PATHS_NOTE at the shell boundary. Library imports still run
        # normally; explicit shell exploration outside the task is rejected.
        first_line = command.split("\n", 1)[0]
        shell_command = first_line if re.search(r"\bpython(?:3)?\b.*<<", first_line) else command
        try:
            lexer = shlex.shlex(shell_command, posix=True, punctuation_chars=";&|<>")
            lexer.whitespace_split = True
            tokens = list(lexer)
        except ValueError:
            return None  # Let the shell report its own syntax error.
        for token in tokens:
            if token.startswith("/") and token != "/dev/null":
                return "Use relative paths under workspace/ or skills/; external filesystem exploration is not allowed."
            if token.startswith("~") or re.match(r"^[A-Za-z]:[\\/]", token) or re.search(r"(^|[\\/])\.\.([\\/]|$)", token):
                return "Paths must remain within the sandbox; use workspace/ or skills/."
            if token in {"find", "grep"}:
                return "Use the glob/grep file tools to search within the sandbox, as required by the execute tool."
        return None
    paths = [str(Path(sys.executable).parent)]
    env = {"HOME": str(sandbox), "PYTHONDONTWRITEBYTECODE": "1",
           "PYTHONIOENCODING": "utf-8"}
    backend_type = LocalShellBackend
    if os.name == "nt":
        system_root = os.environ.get("SystemRoot", r"C:\Windows")
        paths.extend([str(Path(system_root) / "System32"), system_root])
        # Git for Windows provides the POSIX utilities used in the lab tests.
        git_tools = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Git" / "usr" / "bin"
        if git_tools.is_dir():
            paths.append(str(git_tools))
        env["SystemRoot"] = system_root
        bash = git_tools.parent.parent / "bin" / "bash.exe"
        if bash.is_file():
            import subprocess
            from deepagents.backends.protocol import ExecuteResponse

            class GitBashBackend(LocalShellBackend):
                """Use the lab's POSIX command syntax on native Windows."""

                def execute(self, command, *, timeout=None):
                    effective_timeout = self._default_timeout if timeout is None else timeout
                    if effective_timeout <= 0:
                        raise ValueError("timeout must be positive")
                    if not isinstance(command, str) or not command:
                        return ExecuteResponse(output="Error: command must be a non-empty string",
                                               exit_code=1, truncated=False)
                    violation = path_violation(command)
                    if violation:
                        return ExecuteResponse(output=f"Error: {violation}", exit_code=1, truncated=False)
                    try:
                        result = subprocess.run(
                            [str(bash), "--noprofile", "--norc", "-c", command],
                            cwd=str(self.cwd), env=self._env, shell=False,
                            capture_output=True, stdin=subprocess.DEVNULL,
                            encoding="utf-8", errors="replace", timeout=effective_timeout,
                        )
                    except subprocess.TimeoutExpired:
                        return ExecuteResponse(output=f"Error: command timed out after {effective_timeout}s",
                                               exit_code=124, truncated=False)
                    output = result.stdout + "".join(f"[stderr] {line}\n" for line in result.stderr.splitlines())
                    truncated = len(output) > self._max_output_bytes
                    return ExecuteResponse(output=output[:self._max_output_bytes] or "<no output>",
                                           exit_code=result.returncode, truncated=truncated)

            backend_type = GitBashBackend
    else:
        paths.extend(["/usr/local/bin", "/usr/bin", "/bin"])
    env["PATH"] = os.pathsep.join(paths)
    if os.getenv("LAB_SHELL_BACKEND") == "docker":
        import shutil
        import subprocess
        from deepagents.backends.protocol import ExecuteResponse

        docker = shutil.which("docker")
        if docker is None:
            raise RuntimeError("Docker CLI is required for LAB_SHELL_BACKEND=docker")
        image = os.getenv("LAB_SANDBOX_IMAGE", "lab-agent-sandbox:py311")

        class DockerShellBackend(LocalShellBackend):
            """Expose only the task sandbox to the shell, with no network or keys."""

            def execute(self, command, *, timeout=None):
                effective_timeout = self._default_timeout if timeout is None else timeout
                if effective_timeout <= 0:
                    raise ValueError("timeout must be positive")
                if not isinstance(command, str) or not command:
                    return ExecuteResponse(output="Error: command must be a non-empty string",
                                           exit_code=1, truncated=False)
                violation = path_violation(command)
                if violation:
                    return ExecuteResponse(output=f"Error: {violation}", exit_code=1, truncated=False)
                args = [docker]
                if os.name == "nt":
                    args += ["-H", "npipe:////./pipe/dockerDesktopLinuxEngine"]
                args += ["run", "--rm", "--init", "--network", "none", "--read-only",
                         "--pids-limit", "64", "--cap-drop", "ALL", "--security-opt", "no-new-privileges",
                         "--tmpfs", "/tmp:rw,nosuid,size=64m", "--mount",
                         f"type=bind,source={self.cwd},target=/sandbox", "--workdir", "/sandbox",
                         "--env", "HOME=/sandbox", "--env", "PYTHONDONTWRITEBYTECODE=1",
                         "--env", "PYTHONIOENCODING=utf-8", image, "/bin/sh", "-c", command]
                try:
                    result = subprocess.run(args, shell=False, cwd=str(self.cwd), env=self._env,
                                            capture_output=True, stdin=subprocess.DEVNULL,
                                            encoding="utf-8", errors="replace", timeout=effective_timeout)
                except subprocess.TimeoutExpired:
                    return ExecuteResponse(output=f"Error: command timed out after {effective_timeout}s",
                                           exit_code=124, truncated=False)
                output = result.stdout + "".join(f"[stderr] {line}\n" for line in result.stderr.splitlines())
                return ExecuteResponse(output=output[:self._max_output_bytes] or "<no output>",
                                       exit_code=result.returncode,
                                       truncated=len(output) > self._max_output_bytes)

        backend_type = DockerShellBackend
    return backend_type(root_dir=sandbox, virtual_mode=True,
                        inherit_env=False, env=env, timeout=120)


def build_agent(sandbox: Path, mode: str = "single", use_skills: bool = False, model=None):
    """Tạo tác tử Deep Agents.

    Tham số:
      sandbox:    thư mục chứa `workspace/` (và `skills/` nếu có).
      mode:       "single"    -> tác tử mặc định (có subagent `general-purpose` sẵn của Deep Agents)
                  "subagents" -> thêm các subagent từ `get_subagents()` (nối PATHS_NOTE vào `system_prompt` của MỖI subagent,
                                 vì subagent không nhận BASE_PROMPT) và thêm SUBAGENTS_NOTE vào prompt chính
      use_skills: True -> nạp thư mục "/skills/" qua tham số `skills=` của create_deep_agent
                  và thêm SKILLS_NOTE vào prompt.
      model:      mô hình ngôn ngữ; None -> dùng `make_model()`.
    mode không hợp lệ -> ném ValueError.
    Trả về: đồ thị (graph) đã biên dịch, gọi bằng `.invoke({"messages": [...]})`.
    """
    if mode not in {"single", "subagents"}:
        raise ValueError(f"Unknown agent mode: {mode}")
    prompt = BASE_PROMPT
    kwargs = {}
    if mode == "subagents":
        kwargs["subagents"] = [
            {**sub, "system_prompt": sub["system_prompt"] + " " + PATHS_NOTE}
            for sub in get_subagents()
        ]
        prompt += SUBAGENTS_NOTE
    if use_skills:
        kwargs["skills"] = ["/skills/"]
        prompt += SKILLS_NOTE
    return create_deep_agent(model=control_model(model if model is not None else make_model()),
                             system_prompt=prompt, backend=make_backend(sandbox), **kwargs)
