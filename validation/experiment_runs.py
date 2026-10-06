"""Run independent lab tasks with shared request pacing and an audit log.

Usage: python validation/experiment_runs.py --condition baseline --tasks learn
Uses the lab runner; transient infrastructure failures are retried at most once.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import threading

from langchain_core.callbacks import BaseCallbackHandler
from lab.model import make_model
from lab.rate_control import control_model
from lab.runner import run_task
from lab.tasks import ROOT, list_tasks

LOG = ROOT / "report" / "experiment-events.jsonl"
LOCK = threading.Lock()


class Progress(BaseCallbackHandler):
    def __init__(self, task, condition):
        self.task, self.condition = task, condition
        self.calls = 0
        self.lock = threading.Lock()

    def on_llm_end(self, response, **kwargs):
        with self.lock:
            self.calls += 1
            if self.calls % 5 == 0:
                event("progress", task=self.task, condition=self.condition, model_calls=self.calls)


def event(kind, **fields):
    record = {"timestamp": datetime.now(timezone.utc).isoformat(), "event": kind, **fields}
    with LOCK:
        with LOG.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(json.dumps(record, ensure_ascii=False), flush=True)


def run_one(task, condition, results, recursion_limit):
    for attempt in range(1, 3):
        event("start", task=task, condition=condition, results=results, attempt=attempt)
        model = control_model(make_model())
        model = model.model_copy(update={"callbacks": [Progress(task, condition)]})
        record = run_task(task, condition, results_dir=results,
                          recursion_limit=recursion_limit, model=model)
        event("finish", task=task, condition=condition, results=results, attempt=attempt,
              passed=record["passed"], total=record["total"], tokens=record["tokens"]["total"],
              seconds=record["seconds"], error=record["error"],
              skills_read=record["skills_read"], subagent_calls=record["subagent_calls"])
        # A fixed-budget agent failure is a measured outcome, not a reason to
        # spend the same budget again. Retry only recognizable transient faults.
        transient = record["error"] and record["error"].startswith((
            "APIConnectionError:", "OpenAIConnectionError:", "APITimeoutError:",
            "RemoteProtocolError:", "RateLimitError:", "InternalServerError:",
            "ServiceUnavailableError:", "TimeoutError:",
        ))
        if not transient:
            return record
        # Preserve real failed results, never retry to chase a higher task score.
        source = Path(results) / condition / task
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        target = ROOT / "results" / "archive" / f"failed-{stamp}" / condition / task
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, target)
        if attempt == 2:
            return record
    raise AssertionError("unreachable")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--condition", choices=["baseline", "subagents", "skills-auto"], required=True)
    parser.add_argument("--tasks", nargs="+", default=["learn"])
    parser.add_argument("--results", default="results")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--recursion-limit", type=int, default=100)
    parser.add_argument("--backend", choices=["docker", "local"], default="docker")
    args = parser.parse_args()
    # Import model.py loads .env before these reproducible fallback settings.
    os.environ.setdefault("LAB_REQUESTS_PER_MINUTE", "12")
    if args.backend == "docker":
        os.environ["LAB_SHELL_BACKEND"] = "docker"
    else:
        os.environ.pop("LAB_SHELL_BACKEND", None)
    model = make_model()
    event("batch", condition=args.condition, tasks=args.tasks, workers=args.workers,
          recursion_limit=args.recursion_limit, model=getattr(model, "model_name", None),
          temperature=getattr(model, "temperature", None),
          rpm=os.environ["LAB_REQUESTS_PER_MINUTE"], backend=args.backend)
    if args.tasks == ["all"]:
        ids = [task.id for task in list_tasks()]
    elif args.tasks in (["learn"], ["eval"]):
        ids = [task.id for task in list_tasks(args.tasks[0])]
    else:
        ids = args.tasks
    errors = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(run_one, task, args.condition, args.results, args.recursion_limit): task
                   for task in ids}
        for future in as_completed(futures):
            try:
                record = future.result()
                if record["error"] and not record["error"].startswith("GraphRecursionError:"):
                    errors.append(futures[future])
            except Exception as exc:
                event("crash", task=futures[future], error=f"{type(exc).__name__}: {exc}")
                errors.append(futures[future])
    if errors:
        raise SystemExit(f"Unfinished tasks: {errors}")


if __name__ == "__main__":
    main()
