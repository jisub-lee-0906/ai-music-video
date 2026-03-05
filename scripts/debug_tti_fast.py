from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests
import yaml

from ai_mv.core.contracts.prompt_contract import tti_schema
from ai_mv.core.orchestration.bootstrap_guard import apply_profile
from ai_mv.engines.flux_1_dev_tti.mapper import map_tti_workflow
from ai_mv.engines.flux_1_dev_tti.planner import _planner_prompt


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(prog="debug-tti-fast")
    p.add_argument("--config", default="configs/default.yaml")
    p.add_argument("--profile", default="")
    p.add_argument("--shots", type=int, default=2)
    p.add_argument("--timeout", type=int, default=120)
    return p.parse_args()


def load_config(path: str, profile: str) -> dict:
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(cfg, dict):
        raise RuntimeError("config must be yaml object")
    if profile.strip():
        cfg["profile"] = profile.strip()
    apply_profile(cfg)
    return cfg


def build_sections(n: int) -> list[dict]:
    count = max(1, n)
    step = round(16.0 / count, 3)
    out: list[dict] = []
    cur = 0.0
    for _ in range(count):
        out.append({"name": "debug", "start": cur, "end": round(cur + step, 3)})
        cur = round(cur + step, 3)
    return out


def run_ollama(cfg: dict, prompt: str, timeout: int) -> dict:
    integ = cfg["integrations"]
    body = {
        "model": str(integ["ollama_model"]),
        "prompt": prompt,
        "format": tti_schema(),
        "stream": False,
        "keep_alive": "0s",
        "options": {"num_gpu": int(integ["ollama_num_gpu"])}
    }
    base = str(integ["ollama_base_url"]).rstrip("/")
    res = requests.post(f"{base}/api/generate", json=body, timeout=timeout)
    res.raise_for_status()
    raw = res.json()
    parsed = json.loads(str(raw["response"]))
    return {"request": body, "response": parsed}


def first_comfy_payload(cfg: dict, shots: list[dict]) -> dict:
    if not shots or not isinstance(shots[0], dict):
        return {"node.inputs": {}}
    shot = dict(shots[0])
    shot["filename_prefix"] = f"anchors/{shot['shot_id']}_a"
    return map_tti_workflow(cfg, shot)


def main() -> int:
    args = parse_args()
    cfg = load_config(args.config, args.profile)
    cfg["audio"]["song_title"] = "Fast Debug"
    cfg["audio"]["song_description"] = "Short prompt debug"
    cfg["audio"]["lyrics"] = "[Verse]\ncity light"
    prompt = _planner_prompt(cfg, build_sections(args.shots))
    out = run_ollama(cfg, prompt, args.timeout)
    shots = list(out["response"].get("shots", []))
    result = {
        "ollama_request_payload": out["request"],
        "ollama_parsed_response_json": out["response"],
        "comfy_payload_for_first_shot": first_comfy_payload(cfg, shots),
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
