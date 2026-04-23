# ai-music-video 완성 로드맵

> For Hermes: 이 문서는 top-down 검증과 시스템 분석 결과를 바탕으로, 현재 프로젝트를 “구조 완성 + 품질/운영 안정화” 단계에서 실제 publishable 제품 단계로 밀어올리기 위한 우선순위 실행 계획이다.

목표:
- 현재 이미 닫힌 구조를 다시 뒤엎지 않고,
- 가장 큰 병목인 planning/prompting/quality-execution 경계를 순서대로 줄여서,
- fresh live artifact 기준으로도 안정적으로 publishable 판단이 나오는 상태까지 끌어올린다.

아키텍처 원칙:
- 대수술보다 현재 구조를 유지한 채 병목 구간만 정밀하게 줄인다.
- 변경은 항상 TDD → focused tests → full suite → live validation 순서로 검증한다.
- `.analysis/`와 `docs/analysis/`는 증거용 산출물로 유지하되, 기능 커밋은 코드/테스트 중심으로 관리한다.

기술 스택:
- Python
- ACE-Step audio generation
- Flux2 still generation / reference rerender
- LTX IA2V clip generation
- ffmpeg assembly
- structured review / rerender / escalation pipeline

---

## 현재 상태 요약

top-down 검증 결과:
- CLI / bootstrap / doctor / status: green
- orchestration / state / artifact publish: green
- audio planning / style / section / shot / render planning: green
- still / clip generation / workflow mapping: green
- assembly / review / rerender / escalation: green
- 전체 테스트 상태: `498 passed`

현재 명시적 문제:
1. `scheduler.py` dead/broken import surface
2. planning 허브(`render_items.py`)가 prompt/variation/edit_intent/review metadata를 동시에 쥐고 있어 작은 편향이 전파되기 쉬움
3. still candidate selection loop 부재
4. review diagnosis breadth 대비 rerender execution breadth가 일부 좁음
5. review packet / contact sheet 자동화 completeness 부족
6. citypop 외 style lane 품질 편차 큼
7. latest still-side reanchor fix는 fresh planning 기반 live validation이 아직 더 필요

현재 가장 큰 병목 순위:
1. planning 허브 (`plan_mv.py`, `render_items.py`)
2. review → rerender execution 경계
3. still candidate auto-pick
4. lane maturity 편차

---

# Phase 0. 안전 정리 / 죽은 표면 제거

### Task 0-1: broken scheduler surface를 정리한다

Objective:
- 현재 main runtime에는 영향이 없지만, 깨진 표면이 분석/확장 시 혼란을 일으키는 문제를 먼저 제거한다.

Files:
- Modify: `src/ai_mv/core/orchestration/scheduler.py`
- Test: 필요 시 `tests/unit/test_pipeline.py` 또는 새 `tests/unit/test_scheduler_surface.py`

해야 할 일:
1. `scheduler.py`가 진짜 필요한 surface인지 확인한다.
2. 필요 없으면 제거 또는 deprecated wrapper로 바꾼다.
3. 필요하면 `stage_registry` 의존 없이 현재 `pipeline.py`의 ordered stage truth를 참조하게 바꾼다.

검증:
- `python -c "import ai_mv.core.orchestration.scheduler"`
- 관련 focused test
- full suite

완료 기준:
- import error가 사라질 것
- “죽은 orchestration 표면”이 더 이상 남지 않을 것

우선순위:
- 높음(작은 작업, 높은 clarity benefit)

---

# Phase 1. Fresh planning 기반 live validation 재확인

이 phase가 제일 중요하다.
현재 최근 clip contamination reduction은 live에서 일부 확인됐지만,
latest still reanchor fix는 old manifest replay가 아니라 fresh planning 기준으로 다시 검증해야 한다.

### Task 1-1: fresh short live validation run 스크립트를 만든다

Objective:
- old manifest replay가 아니라 최신 planning code가 새 render_plan을 생성하는 fresh run 경로를 만든다.

Files:
- Create: `.analysis/run_fresh_validation_<id>.py`
- Reference:
  - `src/ai_mv/core/orchestration/pipeline.py`
  - `src/ai_mv/core/orchestration/config_defaults.py`
  - `src/ai_mv/core/orchestration/wsl_overrides.py`
  - 기존 `.analysis/run_payoff_rerender_live_contract_r3.py`

해야 할 일:
1. `default_config()`에서 시작
2. 짧은 smoke-friendly config 주입
3. `concept_text`, `audio.brief`, `audio.hook_brief`, `target_duration_sec=18` 설정
4. 새 `run_id`로 `run_pipeline(...)` 실행

검증:
- 스크립트 dry inspection
- WSL bootstrap 확인
- background run launch

### Task 1-2: fresh still prompt emitted text를 저장/검토한다

Objective:
- latest citypop reanchor contract가 실제 fresh render_plan에 반영되는지 검증한다.

Files:
- Read: `artifacts/runs/<run_id>/manifest.json`
- Analyze: `render_plan[*].still_prompt_text`

확인 포인트:
- intro/world-first family에서
  - `no foreground figure`
  - `barely noticeable distant human presence`
  같은 문구가 사라졌는가
- release_wide/skyline_release에서
  - `anchored subject silhouette`
  - `controlled negative space`
  - `readable subject scale`
  로 바뀌었는가

### Task 1-3: fresh clip prompt emitted text를 저장/검토한다

Objective:
- latest clip contamination reduction이 fresh planning에도 반영되는지 확인한다.

확인 포인트:
- intro / bridge / outro:
  - `environment-led camera framing` 없어야 함
  - `restrained camera`여야 함
- verse/support scenic shot:
  - 여전히 environment-led framing이 남을 수 있어야 함
- clip prompt에 still-only 문구가 새지 않아야 함
  - `single cinematic keyframe`
  - `one uninterrupted composition`
  - `no collage`

### Task 1-4: generated still/clip artifact를 shot별로 눈으로 확인한다

Objective:
- emitted prompt 변화가 실제 artifact quality에 반영되는지 본다.

Files:
- Windows ComfyUI output artifacts
- `.analysis/` review packet / frame extraction outputs

필수 샷:
- intro/world-first
- bridge/connective
- outro/release
- 가능하면 chorus/performance 1개

완료 기준:
- 최신 still reanchor fix가 fresh artifact에서도 보일 것
- clip contamination reduction이 prompt history + artifact에서 동시에 확인될 것

우선순위:
- 최상

---

# Phase 2. planning 허브(`render_items.py`) 정밀 분리

### Task 2-1: shared variation의 still/clip translation을 더 분리한다

Objective:
- 현재 shared variation profile이 still/clip을 함께 끌고 가는 coupling을 더 줄인다.

Files:
- Modify: `src/ai_mv/core/planning/render_items.py`
- Test: `tests/unit/test_planning_render_items.py`

방향:
1. still-side framing/environment emphasis는 유지
2. clip-side camera/motion emphasis는 더 role-aware하게 별도 제한
3. `section_type` 기반 clip framing normalization 규칙을 명시적으로 문서화

검증:
- intro / bridge / outro / verse / chorus 각 케이스에 대한 focused tests
- full suite

### Task 2-2: clip prompt를 더 role-specific하게 강화한다

Objective:
- contamination은 줄였지만 아직 generic-safe인 clip prompt를 더 제품적으로 차별화한다.

Files:
- Modify: `src/ai_mv/core/planning/render_items.py`
- Test: `tests/unit/test_planning_render_items.py`, `tests/unit/test_stage_entrypoints.py`

방향:
- intro:
  - neutral but not dead
- bridge:
  - transition/readability 강화
- outro:
  - release but subject payoff 유지
- chorus/performance:
  - performance-led / hook-emphasis 유지
- verse/support:
  - scenic allowance 유지하되 same-world continuity 강화

완료 기준:
- clip_positive_prompt가 section-role별로 더 분명히 갈릴 것
- “전부 비슷하게 안전한 문자열”에서 벗어날 것

우선순위:
- 매우 높음

---

# Phase 3. still candidate selection loop 추가

현재 generation의 구조적 품질 병목은
“후보를 만들지만 고르지 않는 것”이다.

### Task 3-1: still candidate selection policy 설계

Objective:
- first candidate 고정에서 벗어나 최소한의 deterministic selection policy를 둔다.

Files:
- Modify: `src/ai_mv/core/stages/render_stills.py`
- Test: `tests/unit/test_stage_entrypoints.py`

후보 정책 예시:
1. 현재는 candidate_images[0] 사용
2. 향후 최소 정책:
   - existing quality score hook 또는 prompt-policy-based preference
   - 이후 vision/manual review hook로 확장 가능하도록 shape 마련

주의:
- 지금 단계에서는 복잡한 model-based ranking까지 가지 말 것(YAGNI)
- 먼저 selection seam만 열 것

### Task 3-2: render_count 의미를 quality loop에 연결

Objective:
- render_count가 단순 candidate count가 아니라 실제 품질 uplift 지점이 되게 한다.

검증:
- candidate_count > 1인 케이스 test
- selection metadata surface test

우선순위:
- 높음

---

# Phase 4. review → execution coverage 확장

### Task 4-1: 현재 report-only action 목록을 executable 여부로 분류한다

Objective:
- review action vocabulary와 actual execution coverage를 맞춘다.

Files:
- Read/Modify:
  - `src/ai_mv/core/review/publishability.py`
  - `src/ai_mv/core/stages/execute_rerender.py`
  - `src/ai_mv/core/stages/repair_rerender_prompts.py`
- Test:
  - `tests/unit/test_review_subsystem.py`
  - `tests/unit/test_stage_entrypoints.py`

해야 할 일:
1. 현재 recommended_action 목록 추출
2. 실제 executable action 목록 추출
3. mismatch 표 작성
4. action별로:
   - truly executable로 구현하거나
   - manual_only / inspect_only로 명시 downgrade

### Task 4-2: 미구현 fix_strategy 정리

Objective:
- report에는 나오는데 prompt repair가 no-op인 fix_strategy를 줄인다.

완료 기준:
- `publishability.py`가 내보내는 주요 fix_strategy는 `repair_rerender_prompts.py`에 실제 구현 대응이 있을 것
- 또는 intentionally no-op임이 명확히 드러날 것

우선순위:
- 높음

---

# Phase 5. review packet / QA 자동화 완결성 보강

### Task 5-1: review packet 생성 시 frame extraction 연결 여부 결정

Objective:
- 현재 review packet이 scaffold-only인지, frame extraction까지 묶을지 truth를 맞춘다.

Files:
- Modify:
  - `src/ai_mv/analysis/review_packet.py`
  - `src/ai_mv/analysis/frame_extract.py`
  - `src/ai_mv/entrypoints/review_packet.py`
- Test:
  - `tests/unit/test_review_packet.py`
  - `tests/unit/test_frame_extract.py`

선택지:
A. packet는 scaffold-only로 유지하되 문서/CLI를 명확히 수정
B. packet 생성 시 extract-frames까지 실행

현재 제품 완성도 관점에선 B가 더 가치 있음.

### Task 5-2: contact-sheet.png 생성 seam을 닫는다

Objective:
- 현재 manifest target만 있는 contact-sheet image를 실제 생성 가능한 상태로 만든다.

Files:
- Modify:
  - `src/ai_mv/analysis/contact_sheet.py`
  - `src/ai_mv/analysis/review_packet.py`
- Test:
  - `tests/unit/test_contact_sheet.py`

우선순위:
- 중간~높음

---

# Phase 6. style lane maturity 정렬

### Task 6-1: citypop 외 lane thinness audit

Objective:
- lane별 prompting/rules thickness를 비교해 편차를 정량화한다.

Files:
- Read:
  - `src/ai_mv/styles/*/prompting.py`
  - `src/ai_mv/styles/*/rules.py`
- Output:
  - `docs/analysis/lane-maturity-audit.md`

### Task 6-2: 최소 1개 비-citypop lane을 citypop 수준으로 보강

추천 lane:
- `synthwave`

이유:
- 이미 비교적 강하고 prompt framing이 더 보수적이며,
- citypop와 비교 실험도 쉬움

우선순위:
- 중간

---

# Phase 7. truth-source 정리

### Task 7-1: style metadata 이중화 정리

Objective:
- `bible/prompting/rules`와 `signals/modes/materials/review`의 역할을 문서로 명확히 한다.

Files:
- Create/Modify:
  - `docs/analysis/style-truth-source.md`
  - 필요시 `src/ai_mv/styles/__init__.py` 주석/설명 보강

완료 기준:
- runtime source of truth가 어디인지 문서로 명확할 것
- 유지해야 하는 병행 surface와 죽여야 할 surface가 구분될 것

우선순위:
- 중간

---

# 실행 우선순위 요약

## Tier 1 — 바로 해야 하는 것
1. Fresh planning 기반 live validation
2. `render_items.py` 기반 clip prompt role-specific 강화
3. `scheduler.py` dead surface 정리

## Tier 2 — 품질을 눈에 띄게 올리는 것
4. still candidate selection loop 도입
5. review → execution coverage 확장

## Tier 3 — 제품 운영 완성도 마감
6. review packet / contact sheet 자동화 완결
7. lane maturity 정렬
8. style truth-source 정리

---

# 가장 추천하는 바로 다음 실행 슬라이스

다음 한 슬라이스는 이렇게 가는 게 가장 좋다.

### Slice A: fresh-live-validation-and-prompt-truth
Goal:
- 최신 still reanchor + clip contamination reduction이 fresh run에서도 실제 artifact에 반영되는지 확인

Files:
- `.analysis/run_fresh_validation_<id>.py`
- `artifacts/runs/<new_run_id>/manifest.json`
- `artifacts/runs/<new_run_id>/run_summary.json`
- `.analysis/<new_run_id>-validation-notes.md`

완료 기준:
- fresh render_plan prompt 확인
- still/clip artifact 확인
- old replay artifact가 아니라 최신 planning 결과가 반영된 증거 확보

이 슬라이스가 끝나면,
그 다음부터는 진짜로 `render_items.py` refinement를 더 공격적으로 들어가도 된다.

---

# 최종 한 줄 정리

현재 ai-music-video를 완성시키기 위한 최단 경로는:
`fresh live validation으로 최신 계약 반영을 확인하고 -> planning/prompt 허브를 정교화하고 -> review execution gap과 QA completeness를 닫는 것`이다.
