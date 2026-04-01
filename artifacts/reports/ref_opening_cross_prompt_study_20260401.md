# REF Opening-Cross Prompt Study (2026-04-01)

## Goal
- Find a REF prompt shape for `final chorus`-type opening shots where the heroine remains the subject of the image.
- Prevent the doorway, gate, or bright opening from becoming the real protagonist.

## Fixed Setup
- Anchor image:
  - [character_master_00042_.png](C:/Users/Desktop/Documents/ComfyUI/output/anchors/character_master_00042_.png)
- Test family:
  - `final chorus / opening-cross / gate-line`

## Iteration 1
- Prompt:
  - `The same Korean female idol steps through the station doorway in a bright station-side opening at night, one hand guiding past the gate rail.`
- Output:
  - [refstudy_finalchorus_b1_v01_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/refstudy_finalchorus_b1_v01_end_00001_.png)
- Result:
  - Strong identity continuity
  - Good full-body readability
  - The opening is bright but does not swallow the heroine
  - Gate rail contact is very clear
- Mismatch:
  - Both hands lock onto the rails more strongly than expected
  - The frame feels slightly posed and symmetrical
- Assessment:
  - Strong, but a bit over-committed to rail contact

## Iteration 2
- Prompt:
  - `The same Korean female idol with a high ponytail steps through the station doorway in a bright station-side opening at night, one hand guiding past the gate rail.`
- Output:
  - [refstudy_finalchorus_b1_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/refstudy_finalchorus_b1_v02_end_00001_.png)
- Result:
  - Best overall identity continuity
  - Ponytail remains strong
  - The heroine stays dominant in the frame
  - One-hand gate interaction reads naturally
  - The opening remains bright without becoming the only subject
- Mismatch:
  - Slightly more upright and polished than a raw candid frame
- Assessment:
  - Best overall balance

## Iteration 3
- Prompt:
  - `The same Korean female idol crosses the station doorway in a bright station-side opening at night and leaves the gate rail behind her.`
- Output:
  - [refstudy_finalchorus_b1_v03_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/refstudy_finalchorus_b1_v03_end_00001_.png)
- Result:
  - Clean centered crossing image
  - Full-body walking action is very readable
  - Environment is simpler and less sticky than previous failed doorway outputs
- Mismatch:
  - The frame becomes more generic and frontal
  - The contact detail is lost, so the image is less specific than Iteration 2
- Assessment:
  - Strong generic crossing frame, weaker uniqueness

## Best Prompt So Far
- Selected prompt:
  - `The same Korean female idol with a high ponytail steps through the station doorway in a bright station-side opening at night, one hand guiding past the gate rail.`
- Best output:
  - [refstudy_finalchorus_b1_v02_end_00001_.png](C:/Users/Desktop/Documents/ComfyUI/output/keyframes/refstudy_finalchorus_b1_v02_end_00001_.png)

## What This Taught Us

### 1. `steps through` works better than atmosphere-led opening language
- The model responds well when the crossing action is explicit.
- This is better than describing:
  - bright opening
  - end of night
  - glow spreading
  - doorway symbolism

### 2. A single rail/gate contact detail helps keep the frame specific
- `one hand guiding past the gate rail`
- This kept the opening scene from becoming a generic entrance shot.

### 3. Small identity hooks still help
- `with a high ponytail`
- again improved continuity without bloating the prompt into a checklist.

### 4. Simpler crossing prompts are safer but less distinctive
- `crosses the station doorway ... leaves the gate rail behind her`
- gave a clean image
- but lost some of the useful tactile specificity

## Prompt Pattern To Prefer For Opening Shots
- Recommended pattern:
  - `The same Korean female idol [small identity hook] steps through [doorway/opening] in [place], one hand guiding past [rail/gate edge].`

## Prompt Pattern To Avoid For Opening Shots
- Avoid:
  - `the brightest opening`
  - `the night falls back`
  - `platform glow spreads`
  - `laughs under the light`
  - `face lifted toward the light`
- Those phrases tend to make the opening or the mood become the subject instead of the heroine crossing it.

## Combined Rule With Previous Study
- Contact-detail pattern:
  - best for bridge/window/rail/glass shots
- Opening-cross pattern:
  - best for final chorus / doorway / gate line shots
- Shared structure:
  - same heroine
  - one small identity hook when continuity is fragile
  - one body-led action
  - one place anchor
  - one tactile contact detail
