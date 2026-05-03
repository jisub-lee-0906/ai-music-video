# Full-run default entry inputs

This document records the recommended default values to use when starting an ai-music-video full run from the current project state.

The pipeline is concept-text-first. At the CLI boundary the user-facing inputs are intentionally small:

- `--concept-text`: required for an intentional run
- `--run-id`: optional but recommended for traceable validation runs

Everything else should come from the checked-in runtime defaults unless a specific experiment needs an explicit override.

## Recommended default concept_text

Use this as the current baseline full-run input:

```text
alt-pop desert radio music video, one solitary protagonist follows a fading signal across sunrise dunes toward a distant radio tower, quiet uncertainty turning into calm resolve, stable wardrobe silhouette, no crowd, no second protagonist, no city or neon
```

Why this is the preferred default:

- Starts with `alt-pop`, so style resolution is explicit and does not depend on guessing from the concept.
- Keeps the story centered on one protagonist, which directly exercises identity continuity.
- Requires both upper-body identity and full-body/pose continuity without asking the user to name the internal anchor mechanism.
- Avoids legacy contaminated defaults such as red raincoat, short black bob, or fixed Korean-woman identity.
- Avoids city/neon leakage for desert/radio concepts.
- Gives the planner enough action progression for selected pose/action anchors and IA2V clips.
- Keeps the prompt compact enough for the audio lyric-draft validator to pass reliably in preflight.

The earlier longer/descriptive version of this idea failed preflight at the audio stage with `audio lyrics draft contained unexpected trailing text`. Prefer the compact default above until the audio lyric parser/prompt loop is made more tolerant.

Do not put implementation words such as `Flux`, `TTI`, `reference image`, `anchor`, `ComfyUI`, or `white background` into `concept_text`. Those are pipeline policy, not creative user input.

## Recommended run_id

Use a run id that names the validation goal and date:

```text
identity-anchor-fullrun-YYYYMMDD-HHMMSS
```

Example:

```bash
RUN_ID="identity-anchor-fullrun-$(date +%Y%m%d-%H%M%S)"
```

## Full-run command

From the repository root:

```bash
source .venv/bin/activate

CONCEPT_TEXT='alt-pop desert radio music video, one solitary protagonist follows a fading signal across sunrise dunes toward a distant radio tower, quiet uncertainty turning into calm resolve, stable wardrobe silhouette, no crowd, no second protagonist, no city or neon'
RUN_ID="identity-anchor-fullrun-$(date +%Y%m%d-%H%M%S)"

ai-mv start \
  --run-id "$RUN_ID" \
  --concept-text "$CONCEPT_TEXT"
```

This is the normal full-duration path. Do not use `scripts/start-wsl.sh` for a full-duration validation run unless smoke mode is intentionally desired; that wrapper currently enables WSL smoke mode and shortens audio to about 15-20 seconds.

## Preflight command

Use preflight first when validating prompt contracts and plan routing without committing to a full ComfyUI generation run:

```bash
source .venv/bin/activate

CONCEPT_TEXT='alt-pop desert radio music video, one solitary protagonist follows a fading signal across sunrise dunes toward a distant radio tower, quiet uncertainty turning into calm resolve, stable wardrobe silhouette, no crowd, no second protagonist, no city or neon'
RUN_ID="identity-anchor-preflight-$(date +%Y%m%d-%H%M%S)"

ai-mv preflight \
  --run-id "$RUN_ID" \
  --concept-text "$CONCEPT_TEXT"
```

## Runtime defaults to leave unchanged

The current defaults in `src/ai_mv/core/orchestration/config_defaults.py` are appropriate for the baseline full run:

```text
audio.quality: V0
audio.target_duration_min_sec: 150
audio.target_duration_max_sec: 180
video.target: 1920x1080@24
render.flux2_size: 1280x720
render.ltx_ia2v_size: 1280x720
render.ltx_fps: 24
planning.enable_ia2v: true
planning.max_ia2v_shots: 2
planning.ia2v_min_sec: 4.0
planning.ia2v_max_sec: 8.0
runtime.interrupt_comfy_before_start: false
runtime.clear_comfy_queue_before_start: false
```

For shared Windows ComfyUI operation, keep the default non-interrupting behavior unless you explicitly decide to clear or interrupt the queue. The start command will fail if ComfyUI already has running or pending items, which is safer than silently disrupting Krita/Blender work.

## Expected anchor policy for this input

A correct plan should follow this routing:

1. Generate exactly one primary character identity anchor as a Flux2 text-to-image upper-body portrait on a pure white background.
2. Generate full-body and selected pose/action anchors with Flux reference, using the upper-body identity anchor as the reference.
3. Generate shot keyframes with Flux reference from the selected pose/action anchor.
4. Use IA2V only for video clips.
5. Treat world/environment continuity as support only; it must not replace the identity reference path.

Before approving artifact quality, inspect:

- upper-body identity anchor
- full-body anchor
- selected pose/action anchors
- keyframes
- IA2V clips
- final assembly
- `manifest.json`
- `run_summary.json`
- review/rerender evidence

## Post-run validation command

After a successful full run:

```bash
source .venv/bin/activate

ai-mv validate-latest \
  --output-dir .analysis/latest-validation \
  --sample-count 8
```

Use `artifacts/latest_success/manifest.json` to locate the canonical final video path and structured outputs.

## Alternate smoke-test input

When the goal is only to test the citypop/neon path or fast visual routing, use this shorter concept instead:

```text
citypop late-night walk under wet neon lights, missed train, unresolved goodbye turning into quiet resolve, one solitary protagonist, stable dark outerwear silhouette, no second protagonist
```

This is not the preferred full-run identity-anchor validation default; it is a useful secondary style-resolution sanity check.
