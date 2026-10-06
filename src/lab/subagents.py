"""GUIDE Phần 1 - Định nghĩa subagent (tác tử con).   >>> SINH VIÊN CÀI ĐẶT <<<

Pseudo-code: guides/pseudocode/02_subagents.md
Kiểm tra:    pytest tests/test_02_agent.py
"""


def get_subagents() -> list[dict]:
    """Trả về danh sách subagent (ít nhất 2, tên khác nhau).

    Mỗi phần tử là một dict có các khóa bắt buộc:
      "name":          tên duy nhất (chữ thường, có thể có dấu gạch ngang)
      "description":   khi nào tác tử chính nên giao việc cho subagent này (viết như một hướng dẫn hành động)
      "system_prompt": chỉ dẫn cho subagent
    Gợi ý vai trò: explorer (đọc và báo cáo), implementer (thực hiện), reviewer (kiểm tra độc lập).
    """
    return [
        {
            "name": "explorer",
            "description": "Use before changing code or analysing unfamiliar data to inspect files, documentation and schemas.",
            "system_prompt": "Inspect the supplied files, README, docstrings and data samples. Do not modify files. Report relevant facts, constraints, file paths and uncertainties to the coordinator.",
        },
        {
            "name": "implementer",
            "description": "Use to implement a scoped code fix or data/log transformation and run the relevant tests or scripts.",
            "system_prompt": "Carry out the supplied task and all its rules. Inspect relevant files before editing, make focused changes and validate with Python or tests. Never modify skills/. Report changed files, validation results and remaining issues.",
        },
        {
            "name": "reviewer",
            "description": "Use after implementation to independently check outputs, requirements and edge cases before accepting the result.",
            "system_prompt": "Independently verify the supplied requirements against the actual files. Inspect outputs and run relevant checks, including edge cases. Do not modify files. Report evidence for defects or successful checks and any unverified requirements.",
        },
    ]
