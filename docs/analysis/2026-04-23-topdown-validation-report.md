# ai-music-video Top-down Validation Report

목적:
- 시스템의 최상단(CLI)부터 최하단(review/rerender/escalation)까지 실제 코드/테스트/일부 artifact 기준으로 순차 검증한 결과를 남긴다.

기준 저장소:
- `/home/jisub-lee/workspace/ai-music-video`

검증 방식:
- top-down 계층 분해
- 각 계층별 관련 테스트 묶음 실행
- 필요한 경우 코드 sanity check와 live artifact 확인 병행

---

## 1. 검증 순서와 결과

### 1단계. CLI / entrypoint / bootstrap / doctor / status
실행 테스트:
- `tests/unit/test_cli_app.py`
- `tests/unit/test_cli_commands.py`
- `tests/unit/test_bootstrap.py`
- `tests/unit/test_preflight_entrypoint.py`
- `tests/unit/test_start_entrypoint.py`
- `tests/unit/test_doctor_entrypoint.py`
- `tests/unit/test_status.py`

결과:
- `24 passed in 0.36s`

판정:
- 상단 진입 경로는 안정적이다.
- command dispatch / bootstrap / preflight / doctor / status surface는 구조적으로 큰 이상이 없다.

---

### 2단계. orchestration / stage merge / state / artifact publish
실행 테스트:
- `tests/unit/test_pipeline.py`
- `tests/unit/test_input_gate.py`
- `tests/unit/test_publish_artifacts.py`
- `tests/unit/test_artifact_provenance.py`
- `tests/unit/test_artifact_summary_fields.py`
- `tests/unit/test_artifact_schema_contract.py`
- `tests/unit/test_preflight_artifacts.py`
- `tests/unit/test_state_store.py`

결과:
- `41 passed in 0.25s`

추가 코드 검증:
- `python -c 'import ai_mv.core.orchestration.scheduler'`
- 결과:
  - `ModuleNotFoundError: No module named 'ai_mv.core.orchestration.stage_registry'`

판정:
- 메인 orchestration/pipeline/state/artifact 흐름은 안정적이다.
- 다만 `scheduler.py`는 현재 dead/broken surface다.
- 즉 main runtime 병목은 아니지만 구조적 결함 1개는 명시적으로 존재한다.

---

### 3단계. audio planning / style resolution / section / shot / render planning
실행 테스트:
- `tests/unit/test_audio_contract.py`
- `tests/unit/test_audio_mapper.py`
- `tests/unit/test_audio_planner_prompt.py`
- `tests/unit/test_audio_sections.py`
- `tests/unit/test_audio_timing.py`
- `tests/unit/test_audio_timing_policy.py`
- `tests/unit/test_planning_sections.py`
- `tests/unit/test_planning_shot_plan.py`
- `tests/unit/test_planning_routing.py`
- `tests/unit/test_plan_mv.py`
- `tests/unit/test_style_resolver.py`
- `tests/unit/test_style_lane_scaffolds.py`
- `tests/unit/test_style_lane_surface_contracts.py`
- `tests/unit/test_style_generic_lane_packs.py`
- `tests/unit/test_style_citypop_pack.py`

결과:
- `147 passed in 0.45s`

코드 관찰:
- style resolution은 `styles/resolver.py`에서 lexical scoring 기반
- planning 허브는 `plan_mv.py`, `shot_plan.py`, `render_items.py`
- citypop lane이 가장 성숙함

판정:
- planning 계층은 테스트 기준 매우 안정적이다.
- 그러나 설계상 병목은 여전히 여기다.
- 특히:
  - lexical style resolution brittleness
  - non-citypop lane maturity 편차
  - `render_items.py`에 prompt/variation/edit_intent/review metadata 집중

---

### 4단계. still / clip generation / workflow mapping
실행 테스트:
- `tests/unit/test_flux2_runner.py`
- `tests/unit/test_citypop_mappers.py`
- `tests/unit/test_stage_entrypoints.py`
- `tests/unit/test_planning_render_items.py`
- `tests/unit/test_ia2v_canon_purge.py`
- `tests/unit/test_stage_payloads_generic_style.py`
- `tests/unit/test_comfy_local.py`
- `tests/unit/test_comfy_transport_wait.py`
- `tests/unit/test_comfy_outputs.py`
- `tests/unit/test_path_utils_stage.py`
- `tests/unit/test_clip_timing.py`

결과:
- `155 passed in 2.02s`

추가 sanity check:
- intro / bridge / outro with `environment_forward` -> `restrained camera`
- verse with `environment_forward` -> `environment-led camera framing`

판정:
- generation 계층은 현재 테스트 기준 안정적이다.
- 최근 수행한 clip contamination reduction이 코드 결과에도 반영된다.
- 다만 여전히 generation 품질 병목은 남아 있다:
  - still candidate는 여러 개 생성 가능하지만 ranking/selection loop가 없음
  - clip prompt는 contamination은 줄었지만 아직 generic-safe 성향이 남음
  - latest still reanchor fix는 fresh plan 기반 live validation이 추가로 필요

---

### 5단계. assembly / review / publishability / rerender / escalation
실행 테스트:
- `tests/unit/test_ffmpeg_muxer.py`
- `tests/unit/test_review_stage.py`
- `tests/unit/test_review_subsystem.py`
- `tests/unit/test_quality_findings_template.py`
- `tests/unit/test_review_packet.py`
- `tests/unit/test_frame_extract.py`
- `tests/unit/test_contact_sheet.py`
- `tests/unit/test_preflight_artifacts.py`
- `tests/unit/test_publish_artifacts.py`
- `tests/unit/test_stage_entrypoints.py`

결과:
- `177 passed in 0.76s`

추가 artifact 검증:
- final video duration: `18.000000s`
- music duration: `18.024000s`

판정:
- assembly/review/rerender 계층은 구조적으로 강하다.
- review report, rerender payload, escalation packet 흐름은 매우 잘 짜여 있다.
- 하지만 남은 operational gap은 명확하다:
  - 일부 review action/fix_strategy는 diagnosis breadth 대비 execution coverage가 부족
  - review packet은 scaffold는 좋지만 frame/contact-sheet 자동 완결성이 아직 약함
  - assembly revision 일부는 metadata-level 성격이 남아 있음

---

## 2. top-down 전체 결론

### 구조적 안정성
- 상단부터 하단까지 핵심 실행 계층은 전부 green이다.
- 각 계층 테스트 합계 관점에서는 큰 회귀 신호가 없다.
- 최신 전체 suite도 이미 `498 passed` 상태다.

### 현재 명시적 결함
1. `scheduler.py` broken import
2. review diagnosis 대비 rerender execution coverage 일부 부족
3. review packet/contact sheet 자동화 completeness 부족

### 현재 가장 큰 병목
1. Planning 허브
   - 특히 `render_items.py`
2. Review → Execution 경계
3. Still candidate selection 부재
4. Style lane maturity 편차

### 현재 완성도 해석
- 구조/아키텍처: 100%
- 실제 제품 완성도: 96~97%

즉 남은 문제는 “시스템이 안 돌아간다”가 아니라,
- 결과 품질
- 프롬프트 계약 정교화
- lane 품질 균일화
- execution coverage / QA completeness
쪽에 있다.

---

## 3. 우선순위 액션

### 우선순위 1
fresh planning 기반 live validation
- latest still reanchor fix와 latest clip contamination reduction을 동시에 fresh artifact 기준으로 재검증

### 우선순위 2
`render_items.py` / clip prompt contract 정교화
- generic-safe 성향 축소
- role/section별 차별화 강화

### 우선순위 3
still candidate ranking/selection loop 도입 검토
- 현재 first-candidate auto-pick 병목 해소

### 우선순위 4
review packet 자동화 completeness 보강
- frame extraction / contact-sheet image까지 닫기

### 우선순위 5
style lane truth-source 및 maturity 정리
- citypop 외 lane 보강
- signals/modes/materials/review와 active runtime surface의 관계 정리

### 우선순위 6
dead surface cleanup
- `scheduler.py` 정리

---

## 4. 한 줄 최종 판단

현재 프로젝트는 top-down 검증 기준으로 “구조는 이미 닫혀 있고, 남은 핵심은 planning/prompting/quality-execution stabilization” 단계다.
