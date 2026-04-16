from __future__ import annotations

from ai_mv.styles.resolver import build_style_prompt_draft, build_style_prompt_seed, resolve_style_name



def build_render_item(config: dict, concept_text: str, style_name_or_bible, style_bible_or_shot, shot: dict | None = None) -> dict:
    if shot is None:
        style_name = resolve_style_name(concept_text)
        style_bible = style_name_or_bible
        shot = style_bible_or_shot
    else:
        style_name = str(style_name_or_bible)
        style_bible = style_bible_or_shot
    prompt_seed = build_prompt_seed(style_name, concept_text, style_bible, shot)
    prompt_draft = build_prompt_draft(style_name, shot)
    prompt_polish = polish_prompt(prompt_seed, prompt_draft)
    out = {
        "shot_id": shot["shot_id"],
        "render_mode": shot["render_mode"],
        "prompt_seed": prompt_seed,
        "prompt_draft": prompt_draft,
        "prompt_polish": prompt_polish,
        "still_a": "",
        "still_b": str(shot.get("bridge_to_shot_id", "")).strip(),
    }
    if str(shot.get("render_mode", "")) == "ia2v":
        out["audio_segment"] = {
            "start_sec": shot["start_sec"],
            "duration_sec": shot["duration_sec"],
        }
    return out



def build_prompt_seed(style_name: str, concept_text: str, style_bible: dict, shot: dict) -> str:
    return build_style_prompt_seed(style_name, concept_text, style_bible, shot)



def build_prompt_draft(style_name: str, shot: dict) -> str:
    return build_style_prompt_draft(style_name, shot)



def polish_prompt(prompt_seed: str, prompt_draft: str) -> str:
    tokens: list[str] = []
    for block in (prompt_seed, prompt_draft):
        for token in [part.strip() for part in str(block).split(",") if part.strip()]:
            if token not in tokens:
                tokens.append(token)
    return ", ".join(tokens)
