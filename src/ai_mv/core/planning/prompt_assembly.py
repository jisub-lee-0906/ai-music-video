from __future__ import annotations

from ai_mv.styles.resolver import build_style_prompt_draft, build_style_prompt_seed



def build_prompt_bundle(style_name: str, concept_text: str, style_bible: dict, shot: dict) -> dict:
    prompt_seed = build_prompt_seed(style_name, concept_text, style_bible, shot)
    prompt_draft = build_prompt_draft(style_name, shot)
    return {
        "prompt_seed": prompt_seed,
        "prompt_draft": prompt_draft,
        "prompt_polish": polish_prompt(prompt_seed, prompt_draft),
    }



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
