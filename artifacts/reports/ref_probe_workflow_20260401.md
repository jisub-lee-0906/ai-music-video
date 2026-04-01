# REF Probe Workflow (2026-04-01)

## Goal
- Find the strongest `Flux.2.dev REF` prompt grammar by direct image comparison.
- Keep the TTI anchor fixed.
- Change only prompt structure.

## Preferred Loop
1. Pick one shot archetype.
2. Write 3-6 prompt variants for that archetype.
3. Run `ref-v2-probe-batch`.
4. Compare images 1:1.
5. Write a short study document with:
   - prompt
   - output image
   - what matched
   - what drifted
   - best prompt pattern

## CLI

```powershell
python -m ai_mv.cli.app ref-v2-probe-batch `
  --run-id ref-probe-threshold-batch `
  --brief director_brief_example `
  --ref "C:\Users\Desktop\Documents\ComfyUI\output\anchors\character_master_00044_.png" `
  --prompts-file "D:\workspace\ai-music-video\artifacts\probe_inputs\threshold_prompts_20260401.txt" `
  --shot-id-prefix threshold `
  --frame-name end
```

## Current Archetype Studies
- Threshold crossing:
  - [ref_threshold_prompt_study_20260401.md](D:/workspace/ai-music-video/artifacts/reports/ref_threshold_prompt_study_20260401.md)
- Stair descent:
  - [ref_stair_prompt_study_20260401.md](D:/workspace/ai-music-video/artifacts/reports/ref_stair_prompt_study_20260401.md)
- Earlier single-shot bridge study:
  - [ref_single_image_prompt_study_20260401.md](D:/workspace/ai-music-video/artifacts/reports/ref_single_image_prompt_study_20260401.md)

## Current Rule
- Do not search for one universal REF sentence.
- Search for best prompt grammar per shot archetype.
- Then let the planner choose among those grammars.
