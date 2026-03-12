from __future__ import annotations

from ai_mv.core.contracts.prompt_schema import audio_judge_schema
from ai_mv.infra.codex_cli_client import generate_structured


def judge_audio_candidates(config: dict, plan: dict, candidates: list[dict]) -> dict:
    prompt = _judge_prompt(plan, candidates)
    raw = generate_structured(config, prompt, audio_judge_schema())
    winner = int(raw["winner_index"])
    if winner < 0 or winner >= len(candidates):
        raise RuntimeError("audio judge winner out of range")
    return {
        "winner_index": winner,
        "reasoning": str(raw["reasoning"]).strip(),
        "quality_notes": [str(x).strip() for x in raw["quality_notes"] if str(x).strip()],
        "prompt": prompt,
    }


def _judge_prompt(plan: dict, candidates: list[dict]) -> str:
    profile = str(plan.get("profile_summary", "")).strip()
    audio_dir = str(plan.get("audio_direction", "")).strip()
    hook_dir = str(plan.get("hook_direction", "")).strip()
    lang = str(plan.get("language", "")).strip()
    body = "\n\n".join(_candidate_block(idx, cand) for idx, cand in enumerate(candidates))
    return (
        "You are a ruthless A&R judge selecting the best finished song plan. "
        "Return JSON only. No markdown. "
        "Choose the single candidate that feels most like a real release, not just the one that is formally correct. "
        "Judge using: hook/title-worthiness, chorus internal progression, bridge turn, final chorus payoff, outro landing, and fit to the profile world. "
        "Prefer the candidate that sounds inevitable and memorable after one listen. "
        "Penalize weak generic hooks, chorus lines that repeat the same function, bridges that do not truly turn, final choruses that only expand mechanically, and outros that do not feel settled. "
        f"Profile={profile}. Audio direction={audio_dir}. Hook direction={hook_dir}. Lyrics language={lang}. "
        f"Candidates:\n\n{body}"
    )


def _candidate_block(idx: int, candidate: dict) -> str:
    lines = _section_lines(candidate)
    chorus = " | ".join(lines.get("Chorus", []))
    chorus2 = " | ".join(lines.get("Chorus 2", []))
    bridge = " | ".join(lines.get("Bridge", []))
    final = " | ".join(lines.get("Final Chorus", []))
    outro = " | ".join(lines.get("Outro", []))
    genre = str(candidate.get("genre_description", "")).strip()
    bpm = int(candidate.get("bpm", 0))
    key = str(candidate.get("keyscale", "")).strip()
    return (
        f"Candidate {idx}: bpm={bpm}, keyscale={key}. "
        f"genre_description={genre}\n"
        f"Chorus={chorus}\n"
        f"Chorus 2={chorus2}\n"
        f"Bridge={bridge}\n"
        f"Final Chorus={final}\n"
        f"Outro={outro}"
    )


def _section_lines(candidate: dict) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for row in candidate.get("lyrics_blocks", []):
        label = str(row.get("label", "")).strip()
        lines = [str(x).strip() for x in row.get("lines", []) if str(x).strip()]
        if label and lines:
            out[label] = lines
    return out
