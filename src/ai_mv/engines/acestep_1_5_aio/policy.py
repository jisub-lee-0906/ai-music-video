from __future__ import annotations

from collections.abc import Sequence

DEFAULT_BEATS_PER_BAR = 4
DEFAULT_DURATION_BPM = 120
DEFAULT_ENDING_MODE = "clean_resolve"
DEFAULT_ENDING_VOCAL_DENSITY = "medium"
DEFAULT_TERMINAL_END_TAG = True
DEFAULT_ENDING_TAGS: dict[str, list[str]] = {
    "hard_stop": ["clean ending", "hard stop", "decisive final hit"],
    "clean_resolve": ["clean ending", "resolved final lift"],
    "glow_fade": ["clean ending", "gentle synth tail", "soft afterglow"],
    "bittersweet_tail": ["clean ending", "brief emotional tail", "controlled after-image"],
    "anthem_lift": ["clean ending", "anthemic final lift", "open final release"],
}
DEFAULT_LINE_BUDGETS: dict[str, int] = {
    "Intro": 0,
    "Verse 1": 5,
    "Verse 2": 5,
    "Pre-Chorus": 3,
    "Pre-Chorus 2": 3,
    "Chorus": 5,
    "Chorus 2": 5,
    "Final Chorus": 5,
    "Post-Chorus": 2,
    "Bridge": 3,
    "Outro": 0,
}
DEFAULT_SECTION_BARS: dict[str, int] = {
    "intro": 8,
    "verse": 8,
    "verse_1": 8,
    "verse_2": 8,
    "pre_chorus": 8,
    "chorus": 8,
    "post_chorus": 4,
    "bridge": 4,
    "outro": 8,
    "final_chorus_bonus": 8,
}
HOOK_VALIDATION_SECTION_BARS: dict[str, int] = {
    "intro": 4,
    "verse": 0,
    "verse_1": 0,
    "verse_2": 0,
    "pre_chorus": 0,
    "chorus": 8,
    "post_chorus": 4,
    "bridge": 4,
    "outro": 4,
    "final_chorus_bonus": 0,
}
HOOK_VALIDATION_LINE_BUDGETS: dict[str, int] = {
    "Intro": 0,
    "Verse 1": 0,
    "Verse 2": 0,
    "Pre-Chorus": 0,
    "Pre-Chorus 2": 0,
    "Chorus": 2,
    "Chorus 2": 2,
    "Final Chorus": 3,
    "Post-Chorus": 1,
    "Bridge": 2,
    "Outro": 0,
}
PREFERRED_SONGFORM: tuple[tuple[str, str], ...] = (
    ("intro", "Intro"),
    ("verse_1", "Verse 1"),
    ("pre_chorus", "Pre-Chorus"),
    ("chorus", "Chorus"),
    ("verse_2", "Verse 2"),
    ("bridge", "Bridge"),
    ("chorus", "Final Chorus"),
    ("outro", "Outro"),
)
SHORT_FORM_VARIANTS: tuple[tuple[tuple[str, str], ...], ...] = (
    (
        ("intro", "Intro"),
        ("verse_1", "Verse 1"),
        ("pre_chorus", "Pre-Chorus"),
        ("chorus", "Chorus"),
        ("verse_2", "Verse 2"),
        ("bridge", "Bridge"),
        ("chorus", "Final Chorus"),
        ("outro", "Outro"),
    ),
    (
        ("intro", "Intro"),
        ("verse_1", "Verse 1"),
        ("chorus", "Chorus"),
        ("verse_2", "Verse 2"),
        ("bridge", "Bridge"),
        ("chorus", "Final Chorus"),
        ("outro", "Outro"),
    ),
    (
        ("intro", "Intro"),
        ("verse_1", "Verse 1"),
        ("pre_chorus", "Pre-Chorus"),
        ("chorus", "Chorus"),
        ("verse_2", "Verse 2"),
        ("chorus", "Final Chorus"),
        ("outro", "Outro"),
    ),
)
HOOK_VALIDATION_VARIANTS: tuple[tuple[tuple[str, str], ...], ...] = (
    (
        ("intro", "Intro"),
        ("chorus", "Chorus"),
        ("outro", "Outro"),
    ),
)


def audio_policy(config: dict) -> dict:
    audio = _audio_config(config)
    bpm = _coerce_positive_int(audio.get("bpm"), default=0)
    beats_per_bar = _coerce_positive_int(audio.get("beats_per_bar"), default=DEFAULT_BEATS_PER_BAR)
    songform_mode = resolve_songform_mode(audio)
    section_bars = resolve_section_bars(audio, songform_mode=songform_mode)
    override_duration = _explicit_target_duration(audio)
    variants = songform_variants(songform_mode)
    preferred_rows = variants[0] if songform_mode == "hook_validation" and variants else preferred_songform_rows()
    duration = int(override_duration) if override_duration is not None else 0
    return {
        "duration": int(duration),
        "duration_override": override_duration is not None,
        "duration_min_sec": _coerce_positive_int(audio.get("target_duration_min_sec"), default=150),
        "duration_max_sec": _coerce_positive_int(audio.get("target_duration_max_sec"), default=180),
        "songform_mode": songform_mode,
        "bar_lane": bar_lane_summary(preferred_rows, section_bars),
        "songform_variants": variants,
        "beats_per_bar": beats_per_bar,
        "section_bars": section_bars,
        "seed": int(audio.get("seed", 31)),
        "bpm": bpm,
        "quality": str(audio.get("quality", "V0")),
        "keyscale": str(audio.get("keyscale", "")).strip(),
        "ending_mode": _ending_mode(audio),
        "terminal_end_tag": _terminal_end_tag(audio),
        "final_chorus_required": _coerce_bool(audio.get("final_chorus_required"), default=False),
        "outro_required": _coerce_bool(audio.get("outro_required"), default=False),
        "ending_vocal_density": _ending_vocal_density(audio),
        "ending_tags": _ending_tags(audio),
        "line_budgets": resolve_line_budgets(audio, songform_mode=songform_mode),
        "timesignature": str(audio.get("timesignature", "4")).strip() or "4",
        "generate_audio_codes": _coerce_bool(audio.get("generate_audio_codes"), default=True),
        "cfg_scale": float(audio.get("cfg_scale", 2.0) or 2.0),
        "temperature": float(audio.get("temperature", 0.85) or 0.85),
        "top_p": float(audio.get("top_p", 0.9) or 0.9),
        "top_k": int(audio.get("top_k", 0) or 0),
        "min_p": float(audio.get("min_p", 0.0) or 0.0),
        "sampler_steps": _coerce_positive_int(audio.get("sampler_steps"), default=12),
        "sampler_cfg": float(audio.get("sampler_cfg", 1.3) or 1.3),
        "sampler_name": str(audio.get("sampler_name", "euler")).strip() or "euler",
        "scheduler": str(audio.get("scheduler", "simple")).strip() or "simple",
    }


def preferred_songform_rows() -> list[dict[str, str]]:
    return [{"section": sec, "label": label} for sec, label in PREFERRED_SONGFORM]


def short_form_songform_variants() -> list[list[dict[str, str]]]:
    return songform_variants("full_short_form")


def hook_validation_songform_variants() -> list[list[dict[str, str]]]:
    return songform_variants("hook_validation")


def songform_variants(songform_mode: str) -> list[list[dict[str, str]]]:
    raw = HOOK_VALIDATION_VARIANTS if songform_mode == "hook_validation" else SHORT_FORM_VARIANTS
    return [
        [{"section": sec, "label": label} for sec, label in variant]
        for variant in raw
    ]


def compute_duration_from_blocks(blocks: Sequence[dict], bpm: int, beats_per_bar: int, section_bars: dict[str, int]) -> int:
    rows = _rows(blocks)
    if not rows:
        return compute_duration_from_rows(preferred_songform_rows(), bpm, beats_per_bar, section_bars)
    bars = section_bar_plan(rows, section_bars)
    return _bars_to_seconds(sum(bars), bpm, beats_per_bar)


def compute_duration_from_rows(rows: Sequence[dict], bpm: int, beats_per_bar: int, section_bars: dict[str, int]) -> int:
    bars = section_bar_plan(_rows(rows), section_bars)
    return _bars_to_seconds(sum(bars), bpm, beats_per_bar)


def compute_section_windows(
    duration_sec: float,
    rows: Sequence[dict],
    bpm: int,
    beats_per_bar: int,
    section_bars: dict[str, int] | None,
) -> list[dict]:
    normalized_rows = _rows(rows)
    if not normalized_rows:
        raise RuntimeError("lyrics_blocks empty after validation")
    bars = section_bar_plan(normalized_rows, section_bars or DEFAULT_SECTION_BARS)
    total_bars = sum(bars)
    if total_bars <= 0:
        raise RuntimeError("invalid section bar plan")
    out: list[dict] = []
    cursor = 0.0
    for idx, (row, section_bar_count) in enumerate(zip(normalized_rows, bars)):
        seg = float(duration_sec) * (float(section_bar_count) / float(total_bars))
        end = float(duration_sec) if idx == len(normalized_rows) - 1 else min(float(duration_sec), cursor + seg)
        out.append(
            {
                "name": str(row.get("section", "section")).strip().lower(),
                "label": str(row.get("label", "")).strip() or str(row.get("section", "section")).strip().lower(),
                "start_sec": round(cursor, 3),
                "end_sec": round(end, 3),
            }
        )
        cursor = end
    return out


def build_song_timing(
    duration_sec: float,
    rows: Sequence[dict],
    bpm: int,
    beats_per_bar: int,
    section_bars: dict[str, int] | None,
    *,
    detected_beat_times: Sequence[float] | None = None,
    detected_bpm: int = 0,
) -> dict:
    normalized_rows = _rows(rows)
    if not normalized_rows:
        raise RuntimeError("lyrics_blocks empty after validation")
    beats_per_bar = int(beats_per_bar) if int(beats_per_bar) > 0 else DEFAULT_BEATS_PER_BAR
    section_bars = section_bars or DEFAULT_SECTION_BARS
    bar_counts = section_bar_plan(normalized_rows, section_bars)
    total_bars = sum(bar_counts)
    total_beats = max(1, total_bars * beats_per_bar)
    actual_beats = _normalize_times(detected_beat_times or [])
    resolved_bpm = int(detected_bpm) if int(detected_bpm) > 0 else (int(bpm) if int(bpm) > 0 else DEFAULT_DURATION_BPM)
    grid = _project_song_beat_grid(float(duration_sec), total_beats, resolved_bpm, actual_beats)
    sections: list[dict] = []
    cursor = 0
    for idx, (row, bar_count) in enumerate(zip(normalized_rows, bar_counts)):
        beat_count = max(1, int(bar_count) * beats_per_bar)
        start_idx = cursor
        end_idx = min(total_beats, cursor + beat_count)
        if idx == len(normalized_rows) - 1:
            end_idx = total_beats
        sections.append(
            {
                "name": str(row.get("section", "section")).strip().lower(),
                "label": str(row.get("label", "")).strip() or str(row.get("section", "section")).strip().lower(),
                "start_sec": round(grid[start_idx], 3),
                "end_sec": round(grid[end_idx], 3),
                "start_beat_index": start_idx,
                "end_beat_index": end_idx,
            }
        )
        cursor = end_idx
    bar_times = [round(grid[idx], 6) for idx in range(0, len(grid), beats_per_bar)]
    if not bar_times or bar_times[-1] != round(float(duration_sec), 6):
        bar_times.append(round(float(duration_sec), 6))
    return {
        "sections": sections,
        "timing": {
            "detected_bpm": resolved_bpm,
            "beat_times_sec": [round(x, 6) for x in actual_beats],
            "grid_beat_times_sec": [round(x, 6) for x in grid],
            "bar_times_sec": bar_times,
            "beats_per_bar": beats_per_bar,
        },
    }


def resolve_section_bars(audio: dict, *, songform_mode: str | None = None) -> dict[str, int]:
    raw = audio.get("section_bars", {}) if isinstance(audio, dict) else {}
    base = HOOK_VALIDATION_SECTION_BARS if songform_mode == "hook_validation" else DEFAULT_SECTION_BARS
    if raw in ("", None):
        return dict(base)
    if not isinstance(raw, dict):
        raise RuntimeError("audio.section_bars must be a mapping")
    resolved = dict(base)
    for key, value in raw.items():
        name = str(key).strip().lower()
        if not name:
            continue
        resolved[name] = _coerce_bar_multiple(value, label=f"audio.section_bars.{name}")
    return resolved


def resolve_line_budgets(audio: dict, *, songform_mode: str | None = None) -> dict[str, int]:
    resolved = dict(HOOK_VALIDATION_LINE_BUDGETS if songform_mode == "hook_validation" else DEFAULT_LINE_BUDGETS)
    language = str(audio.get("language", "")).strip().lower()
    ending_mode = _ending_mode(audio)
    terminal_end_tag = _terminal_end_tag(audio)
    ending_vocal_density = _ending_vocal_density(audio)
    outro_required = _coerce_bool(audio.get("outro_required"), default=False)
    if language == "ko":
        resolved["Verse 1"] = 4
        resolved["Verse 2"] = 4
        resolved["Pre-Chorus"] = 3
        resolved["Pre-Chorus 2"] = 3
        resolved["Chorus"] = 4
        resolved["Chorus 2"] = 4
        resolved["Final Chorus"] = 5
        resolved["Bridge"] = 2
        resolved["Intro"] = 0
        resolved["Outro"] = 0
    if language == "ja":
        resolved["Verse 1"] = 5
        resolved["Verse 2"] = 5
        resolved["Pre-Chorus"] = 3
        resolved["Pre-Chorus 2"] = 3
        resolved["Chorus"] = 5
        resolved["Chorus 2"] = 5
        resolved["Final Chorus"] = 5
        resolved["Post-Chorus"] = 2
        resolved["Bridge"] = 3
        resolved["Intro"] = 0
        resolved["Outro"] = 0
    if ending_mode == "clean_resolve":
        resolved["Intro"] = min(int(resolved.get("Intro", 0)), 0)
    if outro_required and terminal_end_tag and ending_mode == "clean_resolve":
        resolved["Outro"] = min(int(resolved.get("Outro", 0)), 0)
    return resolved


def resolve_songform_mode(audio: dict) -> str:
    raw = str(audio.get("songform_mode", "")).strip().lower() if isinstance(audio, dict) else ""
    if raw in {"hook_validation", "full_short_form"}:
        return raw
    max_sec = _coerce_positive_int(audio.get("target_duration_max_sec"), default=0) if isinstance(audio, dict) else 0
    if 0 < max_sec <= 45:
        return "hook_validation"
    return "full_short_form"


def section_bar_plan(rows: Sequence[dict], section_bars: dict[str, int]) -> list[int]:
    normalized_rows = _rows(rows)
    if not normalized_rows:
        return []
    out: list[int] = []
    last_chorus_idx = _last_chorus_index(normalized_rows)
    for idx, row in enumerate(normalized_rows):
        section = str(row.get("section", "")).strip().lower()
        label = str(row.get("label", "")).strip().lower()
        bars = _base_bar_count(section, section_bars)
        if section == "chorus" and idx == last_chorus_idx and "final chorus" in label:
            if int(section_bars.get("final_chorus", 0)) > 0:
                bars = int(section_bars["final_chorus"])
            else:
                bars += int(section_bars.get("final_chorus_bonus", 0))
        out.append(max(1, int(bars)))
    return out


def bar_lane_summary(rows: Sequence[dict], section_bars: dict[str, int]) -> str:
    normalized_rows = _rows(rows)
    bars = section_bar_plan(normalized_rows, section_bars)
    compact: list[str] = []
    for row, count in zip(normalized_rows, bars):
        section = str(row.get("section", "")).strip().lower()
        label = str(row.get("label", "")).strip().lower()
        if section == "chorus" and "final chorus" in label:
            compact.append(f"final chorus {count}")
            continue
        compact.append(f"{_lane_name(section)} {count}")
    return ", ".join(compact)


def _explicit_target_duration(audio: dict) -> int | None:
    raw = audio.get("target_duration_sec") if isinstance(audio, dict) else None
    if raw in ("", None):
        return None
    return _coerce_positive_int(raw, default=0, label="audio.target_duration_sec")


def _bars_to_seconds(total_bars: int, bpm: int, beats_per_bar: int) -> int:
    resolved_bpm = int(bpm) if int(bpm) > 0 else DEFAULT_DURATION_BPM
    resolved_beats = int(beats_per_bar) if int(beats_per_bar) > 0 else DEFAULT_BEATS_PER_BAR
    seconds = float(total_bars) * float(resolved_beats) * 60.0 / float(resolved_bpm)
    return max(1, int(round(seconds)))


def _project_song_beat_grid(
    duration_sec: float,
    total_beats: int,
    bpm: int,
    detected_beat_times: Sequence[float],
) -> list[float]:
    if total_beats <= 0:
        return [0.0, round(float(duration_sec), 6)]
    duration_sec = max(0.001, float(duration_sec))
    beats = _normalize_times(detected_beat_times)
    if not beats:
        beat_sec = duration_sec / float(total_beats)
        out = [0.0]
        for idx in range(1, total_beats):
            out.append(round(idx * beat_sec, 6))
        out.append(round(duration_sec, 6))
        return _monotonic_times(out, duration_sec)
    anchor_positions = [0.0]
    anchor_times = [0.0]
    for idx, value in enumerate(beats, start=1):
        anchor_positions.append(float(idx))
        anchor_times.append(float(value))
    anchor_positions.append(float(len(beats) + 1))
    anchor_times.append(duration_sec)
    detected_units = float(len(beats) + 1)
    out = []
    for expected_idx in range(total_beats + 1):
        query = (float(expected_idx) * detected_units) / float(total_beats)
        out.append(round(_interp(anchor_positions, anchor_times, query), 6))
    out[0] = 0.0
    out[-1] = round(duration_sec, 6)
    return _monotonic_times(out, duration_sec)


def _interp(xs: list[float], ys: list[float], query: float) -> float:
    if query <= xs[0]:
        return ys[0]
    if query >= xs[-1]:
        return ys[-1]
    for idx in range(1, len(xs)):
        left_x = xs[idx - 1]
        right_x = xs[idx]
        if query > right_x:
            continue
        left_y = ys[idx - 1]
        right_y = ys[idx]
        span = max(1e-6, right_x - left_x)
        frac = (query - left_x) / span
        return left_y + (right_y - left_y) * frac
    return ys[-1]


def _normalize_times(values: Sequence[float]) -> list[float]:
    out: list[float] = []
    prev = -1.0
    for raw in values:
        try:
            value = round(float(raw), 6)
        except Exception:
            continue
        if value < 0:
            continue
        if prev >= 0 and value <= prev:
            continue
        out.append(value)
        prev = value
    return out


def _monotonic_times(values: list[float], duration_sec: float) -> list[float]:
    out = list(values)
    for idx in range(1, len(out)):
        if out[idx] <= out[idx - 1]:
            out[idx] = min(duration_sec, round(out[idx - 1] + 1e-3, 6))
    out[0] = 0.0
    out[-1] = round(duration_sec, 6)
    return out


def _base_bar_count(section: str, section_bars: dict[str, int]) -> int:
    if section in section_bars:
        return int(section_bars[section])
    if section.startswith("verse_") and "verse" in section_bars:
        return int(section_bars["verse"])
    if section == "chorus" and "final_chorus" in section_bars:
        return int(section_bars["chorus"])
    return int(DEFAULT_SECTION_BARS.get(section, DEFAULT_SECTION_BARS.get("verse", 12)))


def _lane_name(section: str) -> str:
    aliases = {
        "verse_1": "verse 1",
        "verse_2": "verse 2",
        "pre_chorus": "pre",
        "post_chorus": "post",
    }
    return aliases.get(section, section.replace("_", " "))


def _last_chorus_index(rows: Sequence[dict]) -> int:
    indexes = [idx for idx, row in enumerate(rows) if str(row.get("section", "")).strip().lower() == "chorus"]
    return indexes[-1] if indexes else -1


def _rows(rows: Sequence[dict]) -> list[dict]:
    return [dict(row) for row in rows if isinstance(row, dict)]


def _coerce_positive_int(raw: object, default: int, label: str = "") -> int:
    if raw in ("", None):
        return int(default)
    try:
        value = int(raw)
    except Exception as exc:  # pragma: no cover - defensive conversion guard
        if label:
            raise RuntimeError(f"{label} must be an integer") from exc
        return int(default)
    if value <= 0:
        if label:
            raise RuntimeError(f"{label} must be > 0")
        return int(default)
    return value


def _coerce_bar_multiple(raw: object, label: str) -> int:
    value = _coerce_positive_int(raw, default=0, label=label)
    if value % 4 != 0:
        raise RuntimeError(f"{label} must be a multiple of 4")
    return value


def _audio_config(config: dict) -> dict:
    audio = config.get("audio", {}) if isinstance(config, dict) else {}
    return audio if isinstance(audio, dict) else {}


def _ending_mode(audio: dict) -> str:
    raw = str(audio.get("ending_mode", DEFAULT_ENDING_MODE)).strip().lower()
    allowed = {"hard_stop", "clean_resolve", "glow_fade", "bittersweet_tail", "anthem_lift"}
    return raw if raw in allowed else DEFAULT_ENDING_MODE


def _terminal_end_tag(audio: dict) -> bool:
    return _coerce_bool(audio.get("terminal_end_tag"), default=DEFAULT_TERMINAL_END_TAG)

def _ending_vocal_density(audio: dict) -> str:
    raw = str(audio.get("ending_vocal_density", DEFAULT_ENDING_VOCAL_DENSITY)).strip().lower()
    allowed = {"full", "medium", "low", "tail_only"}
    return raw if raw in allowed else DEFAULT_ENDING_VOCAL_DENSITY


def _ending_tags(audio: dict) -> list[str]:
    raw = audio.get("ending_tags", []) if isinstance(audio, dict) else []
    if isinstance(raw, list):
        vals = [str(item).strip() for item in raw if str(item).strip()]
        if vals:
            return vals
    return list(DEFAULT_ENDING_TAGS[_ending_mode(audio)])


def _coerce_bool(raw: object, default: bool) -> bool:
    if raw in ("", None):
        return bool(default)
    if isinstance(raw, bool):
        return raw
    text = str(raw).strip().lower()
    if text in {"1", "true", "yes", "on"}:
        return True
    if text in {"0", "false", "no", "off"}:
        return False
    return bool(default)
