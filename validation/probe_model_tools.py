"""Small real-API check of tool-result handling, without task data or secrets."""
import json
from pathlib import Path
from langchain_core.messages import HumanMessage, ToolMessage
from lab.model import make_model
from lab.rate_control import control_model


def main():
    results = []
    definition = {"type": "function", "function": {
        "name": "lookup_value", "description": "Return the requested value.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }}
    for wrapped in (False, True):
        model = make_model()
        if wrapped:
            model = control_model(model)
        bound = model.bind_tools([definition])
        messages = [HumanMessage(content="Call lookup_value once, then reply with only the value returned by the tool. Do not call it again.")]
        for step in range(3):
            response = bound.invoke(messages)
            results.append({"wrapped": wrapped, "step": step, "content": response.content,
                            "tool_calls": response.tool_calls, "usage": response.usage_metadata})
            messages.append(response)
            if not response.tool_calls:
                break
            messages.extend(ToolMessage(content="42", tool_call_id=call["id"])
                            for call in response.tool_calls)
    Path("report/model-tool-probe.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
