from __future__ import annotations

from ai_mv.styles.resolver import build_style_prompt_draft, build_style_prompt_seed, resolve_style_name



def build_render_item(config: dict, concept_text: str, style_name_or_bible, style_bible_or_shot, shot: dict | None = None) -> dict:
    if shot is None:
        planning = config.get("planning", {}) if isinstance(config, dict) else {}
        default_style_name = str(planning.get("default_style_name", "")).strip() or None
        style_name = resolve_style_name(concept_text, default_style_name=default_style_name)
        style_bible = style_name_or_bible
        shot = style_bible_or_shot
    else:
        style_name = str(style_name_or_bible)
        style_bible = style_bible_or_shot
    prompt_seed = build_prompt_seed(style_name, concept_text, style_bible, shot)
    prompt_draft = build_prompt_draft(style_name, shot)
    prompt_polish = polish_prompt(prompt_seed, prompt_draft)
    render_mode = str(shot["render_mode"]).strip()
    still_prompt_text = build_still_prompt_text(prompt_seed, prompt_draft, prompt_polish)
    clip_prompt_seed = build_clip_prompt_seed(render_mode, shot, prompt_seed)
    clip_positive_prompt = build_clip_positive_prompt(render_mode, shot, clip_prompt_seed)
    out = {
        "shot_id": shot["shot_id"],
        "render_mode": render_mode,
        "prompt_seed": prompt_seed,
        "prompt_draft": prompt_draft,
        "prompt_polish": prompt_polish,
        "still_prompt_text": still_prompt_text,
        "clip_prompt_seed": clip_prompt_seed,
        "clip_positive_prompt": clip_positive_prompt,
        "still_a": "",
        "still_b": str(shot.get("bridge_to_shot_id", "")).strip(),
    }
    if render_mode == "ia2v":
        out["audio_segment"] = {
            "start_sec": shot["start_sec"],
            "duration_sec": shot["duration_sec"],
        }
    return out



def build_prompt_seed(style_name: str, concept_text: str, style_bible: dict, shot: dict) -> str:
    return build_style_prompt_seed(style_name, concept_text, style_bible, shot)



def build_prompt_draft(style_name: str, shot: dict) -> str:
    return build_style_prompt_draft(style_name, shot)



def build_still_prompt_text(prompt_seed: str, prompt_draft: str, prompt_polish: str) -> str:
    return str(prompt_polish or prompt_draft or prompt_seed).strip()



def build_clip_prompt_seed(render_mode: str, shot: dict, prompt_seed: str) -> str:
    role = str(shot.get("shot_role", "")).replace("_", " ").strip()
    visual_mode = str(shot.get("visual_mode", "")).replace("_", " ").strip()
    seed_prefix = str(prompt_seed or "").split(",")[0].strip()
    if render_mode == "flf2v":
        return _join_prompt_tokens(
            [
                seed_prefix,
                "bridge transition",
                role or "continuous handoff",
            ]
        )
    if render_mode == "ia2v":
        return _join_prompt_tokens(
            [
                seed_prefix,
                role or "performance shot",
                visual_mode or "music-responsive motion",
                "stable camera motion",
                "audio-reactive energy",
            ]
        )
    return _join_prompt_tokens(
        [
            seed_prefix,
            role or "cinematic motion beat",
            visual_mode or "single-shot movement",
            "stable motion",
            "preserve subject continuity",
        ]
    )



def build_clip_positive_prompt(render_mode: str, shot: dict, clip_prompt_seed: str) -> str:
    if render_mode == "flf2v":
        return _join_prompt_tokens(
            [
                clip_prompt_seed,
                "matched endpoints",
                "short transition beat",
                "no world change",
            ]
        )
    if render_mode == "ia2v":
        return _join_prompt_tokens(
            [
                clip_prompt_seed,
                "stable performer identity",
                "restrained camera",
                "no abrupt pose change",
            ]
        )
    return _join_prompt_tokens(
        [
            clip_prompt_seed,
            "single continuous motion",
            "no abrupt pose change",
        ]
    )



def polish_prompt(prompt_seed: str, prompt_draft: str) -> str:
    tokens: list[str] = []
    for block in (prompt_seed, prompt_draft):
        for token in [part.strip() for part in str(block).split(",") if part.strip()]:
            if token not in tokens:
                tokens.append(token)
    return ", ".join(tokens)



def _join_prompt_tokens(parts: list[str]) -> str:
    tokens: list[str] = []
    for part in parts:
        value = str(part or "").strip()
        if value and value not in tokens:
            tokens.append(value)
    return ", ".join(tokens)
