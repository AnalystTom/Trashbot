from __future__ import annotations

import argparse
import json
from typing import Any, Dict, Iterator


DEFAULT_DATASET = "nebius/SWE-agent-trajectories"
DEFAULT_SPLIT = "train"


def _require_datasets():
    try:
        from datasets import load_dataset  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "Missing dependency 'datasets'. Install with: python3 -m pip install -e '.[connectors]'"
        ) from exc
    return load_dataset


def _normalize_row(row: Dict[str, Any], row_idx: int) -> Dict[str, Any]:
    instance_id = str(row.get("instance_id") or f"row-{row_idx}")
    model = str(row.get("model_name") or "unknown")
    target = bool(row.get("target", False))
    exit_status = str(row.get("exit_status") or "")

    trace_id = f"swe-agent:{instance_id}:{model}:{row_idx}"

    return {
        "trace_id": trace_id,
        "run_id": trace_id,
        "benchmark_id": "swe-agent-trajectories",
        "model": model,
        "score": 1.0 if target else 0.0,
        "timestamp": "",
        "task_results": [
            {
                "task_id": instance_id,
                "passed": target,
                "exit_status": exit_status,
                "target": target,
            }
        ],
        "metadata": {
            "instance_id": instance_id,
            "generated_patch": row.get("generated_patch", ""),
            "eval_logs": row.get("eval_logs", ""),
            "trajectory": row.get("trajectory", []),
            "source_dataset": DEFAULT_DATASET,
            "source_split": DEFAULT_SPLIT,
        },
    }


def iter_normalized_traces(
    dataset_id: str = DEFAULT_DATASET,
    split: str = DEFAULT_SPLIT,
    limit: int | None = None,
    streaming: bool = True,
) -> Iterator[Dict[str, Any]]:
    load_dataset = _require_datasets()
    ds = load_dataset(dataset_id, split=split, streaming=streaming)

    for idx, row in enumerate(ds):
        if limit is not None and idx >= limit:
            break
        if isinstance(row, dict):
            yield _normalize_row(row, idx)


def export_connector_payload(
    out_path: str,
    dataset_id: str = DEFAULT_DATASET,
    split: str = DEFAULT_SPLIT,
    limit: int | None = None,
    streaming: bool = True,
) -> int:
    traces = list(iter_normalized_traces(dataset_id=dataset_id, split=split, limit=limit, streaming=streaming))
    payload = {"traces": traces}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    return len(traces)


def main() -> int:
    parser = argparse.ArgumentParser(description="Connector for nebius/SWE-agent-trajectories")
    parser.add_argument("--dataset-id", default=DEFAULT_DATASET)
    parser.add_argument("--split", default=DEFAULT_SPLIT)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--streaming", action="store_true", default=True)
    parser.add_argument("--no-streaming", dest="streaming", action="store_false")
    parser.add_argument("--out", required=True, help="Output JSON path (compatible with trace ingestion)")
    args = parser.parse_args()

    count = export_connector_payload(
        out_path=args.out,
        dataset_id=args.dataset_id,
        split=args.split,
        limit=args.limit,
        streaming=args.streaming,
    )
    print(f"Wrote {count} normalized traces to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
