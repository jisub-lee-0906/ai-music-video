from __future__ import annotations


_BLOCKING_PHRASES: tuple[tuple[str, str], ...] = (
    ("foreground_background_duplicate", "foreground protagonist plus"),
    ("foreground_background_duplicate", "foreground duplicate"),
    ("foreground_background_duplicate", "background copy"),
    ("distant_second_red_figure", "distant second red-coated figure"),
    ("distant_second_red_figure", "second red-coated figure"),
    ("distant_second_red_figure", "red-coated bystander"),
    ("duplicate_protagonist", "duplicate protagonist"),
    ("duplicate_protagonist", "second protagonist"),
    ("duplicate_protagonist", "duplicate body"),
    ("double_exposure", "double exposure"),
    ("montage_layout", "montage"),
    ("split_screen_or_collage", "split screen"),
    ("split_screen_or_collage", "collage"),
    ("subject_too_small", "subject too small"),
    ("subject_too_small", "tiny distant subject"),
)


def evaluate_still_for_ia2v(*, still_row: dict, shot: dict, render_item: dict) -> dict:
    reasons: list[str] = []
    reasons.extend(_explicit_blocking_reasons(still_row))
    text = _combined_text(still_row, shot, render_item)
    reasons.extend(_prompt_blocking_reasons(text))
    if _has_microphone_action(text) and not _pose_supports_microphone(still_row, render_item):
        reasons.append("unsupported_microphone_action")
    reasons = _dedupe(reasons)
    return {
        "status": "fail" if reasons else "pass",
        "blocking_reasons": reasons,
    }



def assert_still_passes_ia2v_gate(*, shot_id: str, still_row: dict, shot: dict, render_item: dict) -> None:
    result = evaluate_still_for_ia2v(still_row=still_row, shot=shot, render_item=render_item)
    reasons = result.get("blocking_reasons") if isinstance(result.get("blocking_reasons"), list) else []
    if reasons:
        raise RuntimeError(f"still QA blocked ia2v shot {shot_id}: {', '.join(str(reason) for reason in reasons)}")



def _explicit_blocking_reasons(still_row: dict) -> list[str]:
    still_qa = still_row.get("still_qa") if isinstance(still_row.get("still_qa"), dict) else {}
    reasons = still_qa.get("blocking_reasons") if isinstance(still_qa.get("blocking_reasons"), list) else []
    out = [str(reason).strip() for reason in reasons if str(reason).strip()]
    status = str(still_qa.get("status", "")).strip().lower()
    if status in {"fail", "failed", "block", "blocked"} and not out:
        out.append("explicit_still_qa_failure")
    return out



def _combined_text(still_row: dict, shot: dict, render_item: dict) -> str:
    chunks: list[str] = []
    for row in (still_row, shot, render_item):
        if not isinstance(row, dict):
            continue
        for key in (
            "prompt_text",
            "prompt_seed",
            "still_prompt_text",
            "clip_prompt_seed",
            "clip_positive_prompt",
            "visual_mode",
            "shot_role",
            "story_function",
            "selected_pose_anchor_id",
        ):
            value = str(row.get(key, "")).strip()
            if value:
                chunks.append(value)
    pose_selection = {}
    if isinstance(still_row.get("pose_anchor_selection"), dict):
        pose_selection = still_row["pose_anchor_selection"]
    elif isinstance(render_item.get("pose_anchor_selection"), dict):
        pose_selection = render_item["pose_anchor_selection"]
    for value in pose_selection.values():
        if isinstance(value, list):
            chunks.extend(str(item).strip() for item in value if str(item).strip())
        else:
            text = str(value).strip()
            if text:
                chunks.append(text)
    return " ".join(chunks).lower()



def _prompt_blocking_reasons(text: str) -> list[str]:
    out: list[str] = []
    for reason, phrase in _BLOCKING_PHRASES:
        if phrase in text and not _is_explicitly_negated_phrase(text, phrase):
            out.append(reason)
    return out



def _is_explicitly_negated_phrase(text: str, phrase: str) -> bool:
    negated_markers = (
        f"no {phrase}",
        f"without {phrase}",
        f"avoid {phrase}",
        f"not {phrase}",
        f"never {phrase}",
    )
    return any(marker in text for marker in negated_markers)
def _has_microphone_action(text: str) -> bool:
    return any(marker in text for marker in ("microphone", "mic stand", "handheld mic", "singing into a mic"))



def _pose_supports_microphone(still_row: dict, render_item: dict) -> bool:
    support_text = " ".join(
        str(value).strip()
        for value in (
            still_row.get("selected_pose_anchor_id"),
            render_item.get("selected_pose_anchor_id"),
            _pose_selection_text(still_row),
            _pose_selection_text(render_item),
        )
        if str(value).strip()
    ).lower()
    return "microphone" in support_text or "mic_" in support_text or "_mic" in support_text or "handheld_mic" in support_text



def _pose_selection_text(row: dict) -> str:
    selection = row.get("pose_anchor_selection") if isinstance(row.get("pose_anchor_selection"), dict) else {}
    chunks: list[str] = []
    for value in selection.values():
        if isinstance(value, list):
            chunks.extend(str(item).strip() for item in value if str(item).strip())
        else:
            text = str(value).strip()
            if text:
                chunks.append(text)
    return " ".join(chunks)



def _dedupe(values: list[str]) -> list[str]:
    out: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in out:
            out.append(text)
    return out
