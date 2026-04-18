# Prompt Lab Experiment Log Template

Use one copy of this template per prompt experiment batch.

## Metadata
- date:
- operator:
- workflow_target: still | i2v | ia2v | flf2v
- model/workflow name:
- source workflow JSON or endpoint:
- purpose:
- benchmark_case_ids:

## Fixed Settings
- size / resolution:
- steps:
- cfg / guidance:
- sampler:
- LoRA / adapter state:
- negative prompt / none:
- other fixed settings:

## Variable Under Test
Describe exactly what changed in this batch.

Examples:
- syntax family
- subject phrasing
- environment phrasing
- motion wording
- endpoint wording
- negative prompt wording or explicit absence of negative input
- seed only

## Prompt Variants

### Variant A
- variant_id:
- prompt:
- seed(s):
- hypothesis:

### Variant B
- variant_id:
- prompt:
- seed(s):
- hypothesis:

### Variant C
- variant_id:
- prompt:
- seed(s):
- hypothesis:

## Results by Benchmark Case

### Case: <case_id>
- intended outcome:
- winning variant:
- rejected variants:
- best image/video paths:
- notes:

#### Evaluation
- subject fidelity:
- environment fidelity:
- composition fidelity:
- style fidelity:
- single-scene integrity:
- motion-safe source suitability:
- continuity friendliness:
- artifact tags:

### Case: <case_id>
- intended outcome:
- winning variant:
- rejected variants:
- best image/video paths:
- notes:

#### Evaluation
- subject fidelity:
- environment fidelity:
- composition fidelity:
- style fidelity:
- single-scene integrity:
- motion-safe source suitability:
- continuity friendliness:
- artifact tags:

## Cross-Case Summary
- best-performing syntax pattern:
- consistently bad syntax pattern:
- seed sensitivity observations:
- workflow-specific caveats:
- confidence level:

## Promotion Decision
- promote to ai-mv repo contract?: yes | no | not yet
- if yes, target files:
- if no, blocker:
- next experiment:
