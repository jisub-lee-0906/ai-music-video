# REF Archetype Grammar Map (2026-04-01)

## Purpose
- Build a reusable grammar map for `Flux.2.dev REF`.
- Use direct image evidence, not taste alone.
- Later, the planner should choose among these grammars instead of inventing from scratch.

## Current Best Grammars

### 1. Threshold Crossing
- Study:
  - [ref_threshold_prompt_study_20260401.md](D:/workspace/ai-music-video/artifacts/reports/ref_threshold_prompt_study_20260401.md)
- Best grammar:
  - source surface -> destination surface + contact release
- Best example:
  - `The same Korean female idol with a high ponytail steps off the station threshold onto the wet street at night, one hand leaving the gate rail.`

### 2. Stair Descent
- Study:
  - [ref_stair_prompt_study_20260401.md](D:/workspace/ai-music-video/artifacts/reports/ref_stair_prompt_study_20260401.md)
- Best grammar:
  - continuous stepped surface + continuous handrail contact
- Best example:
  - `The same Korean female idol with a high ponytail steps down the wet station stairs at night, one hand sliding along the metal handrail.`

### 3. Passage Compression
- Study:
  - [ref_passage_prompt_study_20260401.md](D:/workspace/ai-music-video/artifacts/reports/ref_passage_prompt_study_20260401.md)
- Best grammar:
  - wall proximity + forward movement + trailing rail
- Best example:
  - `The same Korean female idol with a high ponytail keeps close to the narrow passage wall at night and moves forward, one hand trailing the metal rail.`

### 4. Platform Edge Forward Walk
- Study:
  - [ref_platform_edge_prompt_study_20260401.md](D:/workspace/ai-music-video/artifacts/reports/ref_platform_edge_prompt_study_20260401.md)
  - [ref_bridge_platform_motion_study_20260403.md](D:/workspace/ai-music-video/artifacts/reports/ref_bridge_platform_motion_study_20260403.md)
- Best grammar:
  - edge geometry near the feet + directional foot change + optional trace detail
- Best example:
  - `The same Korean female idol with a high ponytail takes a crossing step along the wet platform edge at night, the yellow tactile line close at her feet and her footprint trail widening behind her.`

### 5. Gate / Turnstile Pass
- Study:
  - [ref_gate_pass_prompt_study_20260401.md](D:/workspace/ai-music-video/artifacts/reports/ref_gate_pass_prompt_study_20260401.md)
- Best grammar:
  - beyond-the-gate continuation + destination space ahead
- Best example:
  - `The same Korean female idol with a high ponytail moves beyond the turnstile at night, the wet pavement opening ahead of her.`

### 6. Window Contact
- Study:
  - [ref_window_contact_prompt_study_20260401.md](D:/workspace/ai-music-video/artifacts/reports/ref_window_contact_prompt_study_20260401.md)
- Best grammar:
  - direct metal/window-edge contact + forward continuation
- Best example:
  - `The same Korean female idol with a high ponytail moves past the station window edge at night with one hand still tracing the metal frame.`

### 7. Curb Crossing
- Study:
  - [ref_curb_crossing_prompt_study_20260401.md](D:/workspace/ai-music-video/artifacts/reports/ref_curb_crossing_prompt_study_20260401.md)
- Best grammar:
  - literal wet crosswalk + explicit side-of-route blocking + readable crossing stride
- Best example:
  - `The same Korean female idol with a high ponytail steps in from the far left edge of the wet crosswalk at night, leaving most of the road open ahead of her.`
  - `The same Korean female idol with a high ponytail crosses through the middle-right side of the wet crosswalk at night, keeping the same stride alive.`
  - `The same Korean female idol with a high ponytail carries the same stride along the right edge of the wet crosswalk at night, the open road holding to her left.`
  - `The same Korean female idol with a high ponytail walks away from the wet crosswalk into the wider street at night, leaving the crossing behind her.`

### 8. Sidewalk Continuation
- Study:
  - [ref_sidewalk_continuation_prompt_study_20260401.md](D:/workspace/ai-music-video/artifacts/reports/ref_sidewalk_continuation_prompt_study_20260401.md)
- Best grammar:
  - sidewalk-edge locomotion + one-sided road relation + optional changed-angle re-entry
- Best example:
  - `The same Korean female idol with a high ponytail carries the same stride along the wet sidewalk edge at night, the road still riding to her right.`
  - `The same Korean female idol with a high ponytail commits one step farther from the road-side edge of the wet sidewalk edge outside the station at night and keeps the station block stretching behind her.`

### 9. Doorway Handoff
- Study:
  - [ref_doorway_handoff_prompt_study_20260401.md](D:/workspace/ai-music-video/artifacts/reports/ref_doorway_handoff_prompt_study_20260401.md)
- Best grammar:
  - doorway crossing + literal destination space beyond
- Best example:
  - `The same Korean female idol with a high ponytail clears the doorway at night and carries her next step into the wet passage beyond.`

### 10. Brace / Pause
- Study:
  - [ref_brace_pause_prompt_study_20260401.md](D:/workspace/ai-music-video/artifacts/reports/ref_brace_pause_prompt_study_20260401.md)
- Best grammar:
  - one braced hand on a literal wet rail + forward line still implied
- Best example:
  - `The same Korean female idol with a high ponytail catches one brief pause at the wet rail at night, one hand braced on the bar and her line still forward.`

### 11. Ramp / Underpass Descent
- Study:
  - [ref_ramp_descent_prompt_study_20260401.md](D:/workspace/ai-music-video/artifacts/reports/ref_ramp_descent_prompt_study_20260401.md)
- Best grammar:
  - slope descent + trailing rail
- Best example:
  - `The same Korean female idol with a high ponytail moves lower along the underpass ramp at night, one hand trailing the metal rail.`

### 12. Turn Back Once
- Study:
  - [ref_turn_back_once_prompt_study_20260402.md](D:/workspace/ai-music-video/artifacts/reports/ref_turn_back_once_prompt_study_20260402.md)
- Best grammar:
  - over-shoulder look-back + explicit forward continuation
- Best example:
  - `The same Korean female idol with a high ponytail looks back over one shoulder on the wet street at night while her next step keeps going.`

### 13. Indoor Corridor
- Study:
  - [ref_indoor_corridor_prompt_study_20260402.md](D:/workspace/ai-music-video/artifacts/reports/ref_indoor_corridor_prompt_study_20260402.md)
- Best grammar:
  - narrow corridor volume + wall proximity + forward continuation
- Best example:
  - `The same Korean female idol with a high ponytail moves forward through the narrow indoor corridor at night, the wall staying close at her side.`

### 14. Bench Rest
- Study:
  - [ref_bench_rest_prompt_study_20260402.md](D:/workspace/ai-music-video/artifacts/reports/ref_bench_rest_prompt_study_20260402.md)
- Best grammar:
  - seated rest + small continuation hint
- Best example:
  - `The same Korean female idol with a high ponytail sits at the end of the wet bench at night, one foot still planted as if she could rise again.`

## Shared Structural Rules
- keep one heroine
- keep one small identity hook when continuity matters
- keep one dominant surface/path before strengthening motion
- keep one dominant action
- use one support contact or trace detail only if it helps the archetype
- when motion needs to increase, prefer directional foot-change language over arm-swing or shoulder-turn exaggeration
- in this workflow, compact natural prose usually outperforms heavier identity padding, style padding, or JSON prompt formatting
- avoid symbolic optical language as the main event
- when MV staging matters, physical blocking language works better than camera-meta language
- `far-left edge`, `road-side edge`, `middle-right side`, `right edge`, and `walks away` are more reliable than abstract words like `recedes`, `off-center`, or `left third`

## Shared Failure Modes
- `passes through` often over-inflates machines and doorways
- `clears ... behind her` often erases the current archetype
- `threads through` often widens the space
- `holding/resting` often makes the shot posed
- gesture-first motion often becomes a pose or dance frame
- content-only detail often invents the wrong environment
- `reflection/glow/window` become dangerous when they stop being surface details and become the scene subject

## Current Strategy
- Do not look for a single universal REF sentence.
- Build a planner that classifies shot archetype first.
- Then let the planner choose the matching prompt grammar for that archetype.
