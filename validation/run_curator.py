"""Run the real curator once and persist usage/provenance without editing skills."""
from datetime import datetime, timezone
import json
import time
from pathlib import Path
import argparse
from langchain_core.callbacks import UsageMetadataCallbackHandler
from lab.curator import curate_skills
from lab.model import make_model
from lab.rate_control import control_model
from lab.tasks import hash_skills


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="skills/auto")
    args = parser.parse_args()
    history_path = Path("report/curator-history.json")
    if history_path.exists():
        history = json.loads(history_path.read_text(encoding="utf-8"))
    elif Path("report/curator-run.json").exists():
        history = [json.loads(Path("report/curator-run.json").read_text(encoding="utf-8"))]
    else:
        history = []
    usage = UsageMetadataCallbackHandler()
    model = control_model(make_model()).model_copy(update={"callbacks": [usage]})
    started = time.perf_counter()
    timestamp = datetime.now(timezone.utc).isoformat()
    paths = curate_skills(model=model, out_dir=args.out_dir)
    result = {"timestamp": timestamp, "model": model.inner.model_name,
              "source_condition": "baseline", "source_role": "learn",
              "seconds": round(time.perf_counter() - started, 1),
              "tokens": {label: sum(item.get(key, 0) for item in usage.usage_metadata.values())
                         for label, key in (("input", "input_tokens"), ("output", "output_tokens"), ("total", "total_tokens"))},
              "skills": [str(p) for p in paths], "skills_sha256": hash_skills(Path(args.out_dir)),
              "output_dir": args.out_dir, "reported_models": list(usage.usage_metadata),
              "manual_edits": False, "primary_curator_calls": len(history) + 1}
    history.append(result)
    history_path.write_text(json.dumps(history, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    Path("report/curator-run.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    if not paths:
        raise SystemExit("No valid skills generated")


if __name__ == "__main__":
    main()
