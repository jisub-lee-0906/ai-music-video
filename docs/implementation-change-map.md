# Implementation Change Map

이 문서는 현재 저장소를 기준으로 실제 수정 대상을 파일 단위로 분류한 실행용 맵이다.

분류 기준:

- `Replace Now`
  새 파이프라인 진입점이라 즉시 교체해야 하는 파일

- `Delete After Skeleton`
  새 skeleton이 붙으면 바로 제거 가능한 파일

- `Keep And Adapt`
  재사용 가치가 높아서 내부 계약만 바꿔 쓰는 파일

- `Create New`
  새 파이프라인을 위해 추가해야 하는 파일

- `Test Replace`
  레거시 테스트를 버리고 새 테스트로 교체해야 하는 파일

## 1. Replace Now

이 그룹은 새 아키텍처의 출발점이라 우선 교체해야 한다.

### [workflow_names.py](/D:/workspace/ai-music-video/src/ai_mv/core/workflow_names.py)

현재 역할:

- `AUDIO_WORKFLOW`
- `TTI_WORKFLOW`
- `FLUX2_REF_WORKFLOW`
- `WAN_WORKFLOW`

문제:

- 현재 상수 이름이 새 workflow 집합과 전혀 맞지 않는다.
- doctor/preflight/runtime check가 모두 이 상수에 묶여 있다.

교체 방향:

- `AUDIO_WORKFLOW`
- `QWEN_STILL_WORKFLOW`
- `LTX_I2V_WORKFLOW`
- `LTX_IA2V_WORKFLOW`
- `LTX_FLF2V_WORKFLOW`

영향:

- doctor
- mapper/runner
- bootstrap
- tests

### [doctor_checks.py](/D:/workspace/ai-music-video/src/ai_mv/infra/doctor_checks.py)

현재 역할:

- workflow 템플릿 존재 검사
- ffmpeg/ffprobe 존재 검사

문제:

- 구 workflow 이름에 묶여 있음

교체 방향:

- 새 5개 workflow만 검사
- 향후 M1/M2/M3 단계별 optional check가 필요하면 여기서 분기

### [pipeline.py](/D:/workspace/ai-music-video/src/ai_mv/core/orchestration/pipeline.py)

현재 역할:

- `audio -> storyboard -> keyframes -> clips -> merge`

문제:

- `director_brief`, `story_profile`, `storyboard`, `wan_interpolation` 전제

교체 방향:

- `audio -> plan -> stills -> clips -> assemble -> review`
- 초기 payload에서 `story_profile` 제거
- `citypop_bible` 또는 새 기본 preset 주입

### [README.md](/D:/workspace/ai-music-video/README.md)

문제:

- 사용자 진입점 설명이 모두 레거시 기준

교체 방향:

- 새 workflow 5개
- 새 stage
- 새 입력 스펙
- 새 CLI 기대 흐름 반영

### [config_defaults.py](/D:/workspace/ai-music-video/src/ai_mv/core/orchestration/config_defaults.py)

현재 문제:

- old render defaults와 old workflow 전제가 남아 있을 가능성이 높다.

교체 방향:

- M1에 필요한 최소 기본값만 남긴다.
- `i2v` 중심 기본값부터 잠근다.

### [input_gate.py](/D:/workspace/ai-music-video/src/ai_mv/core/orchestration/input_gate.py)

현재 문제:

- old stage 이름과 payload key를 검증할 가능성이 높다.

교체 방향:

- 새 6 stage와 새 payload key 기준으로 최소 검증만 수행

### Artifact Entry Files

- [publish.py](/D:/workspace/ai-music-video/src/ai_mv/core/artifacts/publish.py)
- [manifest.py](/D:/workspace/ai-music-video/src/ai_mv/core/artifacts/manifest.py)
- [run_summary.py](/D:/workspace/ai-music-video/src/ai_mv/core/artifacts/run_summary.py)

현재 문제:

- 레거시 payload에 강하게 묶여 있다.

교체 방향:

- M1에서는 최소 contract만 유지하거나 임시 단순 구현으로 축소

## 2. Delete After Skeleton

이 그룹은 새 stage skeleton이 import 에러 없이 붙은 뒤 제거 가능하다.

### Stage Files

- [director_plan.py](/D:/workspace/ai-music-video/src/ai_mv/core/stages/director_plan.py)
- [flux2_ref_chain.py](/D:/workspace/ai-music-video/src/ai_mv/core/stages/flux2_ref_chain.py)
- [keyframes.py](/D:/workspace/ai-music-video/src/ai_mv/core/stages/keyframes.py)
- [lyrics_timeline.py](/D:/workspace/ai-music-video/src/ai_mv/core/stages/lyrics_timeline.py)
- [render_plan.py](/D:/workspace/ai-music-video/src/ai_mv/core/stages/render_plan.py)
- [render_verbalizer.py](/D:/workspace/ai-music-video/src/ai_mv/core/stages/render_verbalizer.py)
- [scene_plan.py](/D:/workspace/ai-music-video/src/ai_mv/core/stages/scene_plan.py)
- [storyboard.py](/D:/workspace/ai-music-video/src/ai_mv/core/stages/storyboard.py)
- [tti_anchor.py](/D:/workspace/ai-music-video/src/ai_mv/core/stages/tti_anchor.py)
- [wan_interpolation.py](/D:/workspace/ai-music-video/src/ai_mv/core/stages/wan_interpolation.py)

삭제 조건:

- 새 `plan`, `stills`, `clips`, `assemble`, `review` stage가 import 가능
- `pipeline.py`가 더 이상 위 파일을 참조하지 않음

### Engine Directories

- [flux_2_dev_ref](/D:/workspace/ai-music-video/src/ai_mv/engines/flux_2_dev_ref)
- [flux_2_dev_tti](/D:/workspace/ai-music-video/src/ai_mv/engines/flux_2_dev_tti)
- [wan_2_2_flf2v](/D:/workspace/ai-music-video/src/ai_mv/engines/wan_2_2_flf2v)
- [director_plan](/D:/workspace/ai-music-video/src/ai_mv/engines/director_plan)
- [lyrics_timeline](/D:/workspace/ai-music-video/src/ai_mv/engines/lyrics_timeline)
- [render_plan](/D:/workspace/ai-music-video/src/ai_mv/engines/render_plan)
- [scene_plan](/D:/workspace/ai-music-video/src/ai_mv/engines/scene_plan)

### Entrypoints

- [ref_probe.py](/D:/workspace/ai-music-video/src/ai_mv/entrypoints/ref_probe.py)
- [ref_probe_batch.py](/D:/workspace/ai-music-video/src/ai_mv/entrypoints/ref_probe_batch.py)
- [tti.py](/D:/workspace/ai-music-video/src/ai_mv/entrypoints/tti.py)

## 3. Keep And Adapt

이 그룹은 새 파이프라인에서도 살아남을 가능성이 높다.

### [acestep_music.py](/D:/workspace/ai-music-video/src/ai_mv/core/stages/acestep_music.py)

유지 이유:

- 이미 ACE-Step stage shell이 있음
- 새 입력 계약만 바꿔도 재사용 가치가 큼

수정 포인트:

- `story_profile` 의존 제거
- `music_plan`을 `concept_text` 기반으로 재작성
- profile 기반 context 제거

주의:

- 하위 `acestep_1_5_aio` 엔진은 바로 재사용 가능한지 추가 검토가 필요하다.
- stage shell만 재사용하고 엔진은 분리 신설할 가능성을 열어둔다.

### [ffmpeg_muxer.py](/D:/workspace/ai-music-video/src/ai_mv/core/stages/ffmpeg_muxer.py)

유지 이유:

- concat/mux 유틸은 여전히 필요

수정 포인트:

- WAN chain 전제가 없는 assemble contract로 래핑

### [stage_io.py](/D:/workspace/ai-music-video/src/ai_mv/core/contracts/stage_io.py)

유지 이유:

- stage 입출력 dataclass는 여전히 유효

### [stage_runs.py](/D:/workspace/ai-music-video/src/ai_mv/core/orchestration/stage_runs.py)

유지 이유:

- stage orchestration 공통 계층

주의:

- payload key 검증은 새 기준으로 바뀔 수 있음

### [state_store.py](/D:/workspace/ai-music-video/src/ai_mv/core/state/state_store.py)
- [state_snapshot.py](/D:/workspace/ai-music-video/src/ai_mv/core/state/state_snapshot.py)
- [state_models.py](/D:/workspace/ai-music-video/src/ai_mv/core/state/state_models.py)

유지 이유:

- run 상태 관리 공통 기반

### Infra

- [comfy_client.py](/D:/workspace/ai-music-video/src/ai_mv/infra/comfy_client.py)
- [comfy_local.py](/D:/workspace/ai-music-video/src/ai_mv/infra/comfy_local.py)
- [comfy_outputs.py](/D:/workspace/ai-music-video/src/ai_mv/infra/comfy_outputs.py)
- [comfy_transport.py](/D:/workspace/ai-music-video/src/ai_mv/infra/comfy_transport.py)
- [workflow_patcher.py](/D:/workspace/ai-music-video/src/ai_mv/infra/workflow_patcher.py)

유지 이유:

- workflow submit/patch/output 추출 공통 기반

### Utils

- [audio_timing.py](/D:/workspace/ai-music-video/src/ai_mv/utils/audio_timing.py)
- [path_utils.py](/D:/workspace/ai-music-video/src/ai_mv/utils/path_utils.py)
- [project_root.py](/D:/workspace/ai-music-video/src/ai_mv/utils/project_root.py)
- [text_utils.py](/D:/workspace/ai-music-video/src/ai_mv/utils/text_utils.py)
- [time_utils.py](/D:/workspace/ai-music-video/src/ai_mv/utils/time_utils.py)

유지 이유:

- 장르와 무관한 공통 유틸

## 4. Replace Later

이 그룹은 새 구조가 어느 정도 올라온 뒤 교체하는 편이 안전하다.

### [director_brief.py](/D:/workspace/ai-music-video/src/ai_mv/core/director_brief.py)

현재 문제:

- profile 기반 상위 intent의 중심축

교체 방향:

- `citypop_bible.py`와 `concept_text` 해석 레이어로 분리

### [quality_review.py](/D:/workspace/ai-music-video/src/ai_mv/core/quality_review.py)
- [quality_review_metrics.py](/D:/workspace/ai-music-video/src/ai_mv/core/quality_review_metrics.py)

현재 문제:

- prompt/route 중심 검수

교체 방향:

- 결과물 파일 기준 검수
- rerender target 중심 리포트

### [manifest.py](/D:/workspace/ai-music-video/src/ai_mv/core/artifacts/manifest.py)
- [publish.py](/D:/workspace/ai-music-video/src/ai_mv/core/artifacts/publish.py)
- [run_summary.py](/D:/workspace/ai-music-video/src/ai_mv/core/artifacts/run_summary.py)

현재 문제:

- `flux2_ref_images`, `clip_routes`, `prompt_plan` 같은 레거시 payload를 전제

교체 방향:

- `still_results`, `clip_results`, `review_report` 중심으로 재작성

### [config_defaults.py](/D:/workspace/ai-music-video/src/ai_mv/core/orchestration/config_defaults.py)

현재 문제:

- old render 옵션이 섞여 있을 가능성이 높음

교체 방향:

- `ltx_i2v`, `ltx_ia2v`, `ltx_flf2v` 기준 기본값으로 축소

### [input_gate.py](/D:/workspace/ai-music-video/src/ai_mv/core/orchestration/input_gate.py)

현재 문제:

- 레거시 payload와 stage 이름을 검증할 가능성이 높음

교체 방향:

- 새 payload contract 기준으로 단순화

## 5. Create New

새 파이프라인을 위해 반드시 추가해야 하는 파일들이다.

### Presets

- [citypop_bible.py](/D:/workspace/ai-music-video/src/ai_mv/presets/citypop_bible.py)

역할:

- style rules
- motifs
- negative rules
- section defaults
- prompt seed fragments

### Stage Files

- [plan_citypop_mv.py](/D:/workspace/ai-music-video/src/ai_mv/core/stages/plan_citypop_mv.py)
- [render_stills.py](/D:/workspace/ai-music-video/src/ai_mv/core/stages/render_stills.py)
- [render_clips.py](/D:/workspace/ai-music-video/src/ai_mv/core/stages/render_clips.py)
- [assemble_mv.py](/D:/workspace/ai-music-video/src/ai_mv/core/stages/assemble_mv.py)
- [review_outputs.py](/D:/workspace/ai-music-video/src/ai_mv/core/stages/review_outputs.py)

### Engine Directories

- [acestep_audio](/D:/workspace/ai-music-video/src/ai_mv/engines/acestep_audio)
- [citypop_plan](/D:/workspace/ai-music-video/src/ai_mv/engines/citypop_plan)
- [qwen_stills](/D:/workspace/ai-music-video/src/ai_mv/engines/qwen_stills)
- [ltx_i2v](/D:/workspace/ai-music-video/src/ai_mv/engines/ltx_i2v)
- [ltx_ia2v](/D:/workspace/ai-music-video/src/ai_mv/engines/ltx_ia2v)
- [ltx_flf2v](/D:/workspace/ai-music-video/src/ai_mv/engines/ltx_flf2v)
- [review](/D:/workspace/ai-music-video/src/ai_mv/engines/review)

### Contracts

- [citypop_plan_schema.py](/D:/workspace/ai-music-video/src/ai_mv/core/contracts/citypop_plan_schema.py)
- [render_plan_schema.py](/D:/workspace/ai-music-video/src/ai_mv/core/contracts/render_plan_schema.py)
- [review_report_schema.py](/D:/workspace/ai-music-video/src/ai_mv/core/contracts/review_report_schema.py)

M1 contract 축소:

- M1에서는 contract 파일을 한 번에 모두 만들지 않아도 된다.
- 우선 `review_report_schema.py`와 최소 `render_plan` contract만 먼저 만든다.
- `citypop_plan_schema.py`는 단순 dict contract로 시작하고 이후 분리 가능하다.

## 6. Test Replace

### Delete And Replace

- [test_director_brief.py](/D:/workspace/ai-music-video/tests/unit/test_director_brief.py)
- [test_flux_2_dev_ref_chain_runner.py](/D:/workspace/ai-music-video/tests/unit/test_flux_2_dev_ref_chain_runner.py)
- [test_flux_2_dev_ref_runner.py](/D:/workspace/ai-music-video/tests/unit/test_flux_2_dev_ref_runner.py)
- [test_flux_2_dev_tti_runner.py](/D:/workspace/ai-music-video/tests/unit/test_flux_2_dev_tti_runner.py)
- [test_lyrics_timeline_prompt.py](/D:/workspace/ai-music-video/tests/unit/test_lyrics_timeline_prompt.py)
- [test_media_resolver.py](/D:/workspace/ai-music-video/tests/unit/test_media_resolver.py)
- [test_prompt_normalize.py](/D:/workspace/ai-music-video/tests/unit/test_prompt_normalize.py)
- [test_quality_review.py](/D:/workspace/ai-music-video/tests/unit/test_quality_review.py)
- [test_render_verbalizer.py](/D:/workspace/ai-music-video/tests/unit/test_render_verbalizer.py)
- [test_visual_planners.py](/D:/workspace/ai-music-video/tests/unit/test_visual_planners.py)

새 테스트 후보:

- [test_citypop_plan.py](/D:/workspace/ai-music-video/tests/unit/test_citypop_plan.py)
- [test_qwen_stills_mapper.py](/D:/workspace/ai-music-video/tests/unit/test_qwen_stills_mapper.py)
- [test_ltx_i2v_mapper.py](/D:/workspace/ai-music-video/tests/unit/test_ltx_i2v_mapper.py)
- [test_ltx_ia2v_mapper.py](/D:/workspace/ai-music-video/tests/unit/test_ltx_ia2v_mapper.py)
- [test_ltx_flf2v_mapper.py](/D:/workspace/ai-music-video/tests/unit/test_ltx_flf2v_mapper.py)
- [test_review_outputs.py](/D:/workspace/ai-music-video/tests/unit/test_review_outputs.py)
- [test_pipeline_v2.py](/D:/workspace/ai-music-video/tests/unit/test_pipeline_v2.py)

### Keep And Update

- [test_pipeline.py](/D:/workspace/ai-music-video/tests/unit/test_pipeline.py)
- [test_doctor_checks.py](/D:/workspace/ai-music-video/tests/unit/test_doctor_checks.py)
- [test_bootstrap.py](/D:/workspace/ai-music-video/tests/unit/test_bootstrap.py)
- [test_mappers.py](/D:/workspace/ai-music-video/tests/unit/test_mappers.py)
- [test_pipeline_smoke.py](/D:/workspace/ai-music-video/tests/integration/test_pipeline_smoke.py)
- [test_start_entrypoint.py](/D:/workspace/ai-music-video/tests/unit/test_start_entrypoint.py)
- [test_preflight_entrypoint.py](/D:/workspace/ai-music-video/tests/unit/test_preflight_entrypoint.py)
- [test_status.py](/D:/workspace/ai-music-video/tests/unit/test_status.py)

필수 신규 테스트:

- [test_m1_sample_run.py](/D:/workspace/ai-music-video/tests/integration/test_m1_sample_run.py)
- [test_release_gate_metrics.py](/D:/workspace/ai-music-video/tests/integration/test_release_gate_metrics.py)
- [test_citypop_plan_acceptance.py](/D:/workspace/ai-music-video/tests/unit/test_citypop_plan_acceptance.py)
- [test_review_report_contract.py](/D:/workspace/ai-music-video/tests/unit/test_review_report_contract.py)

## 7. First Execution Slice

실제 구현 착수 순서는 아래로 고정하는 것이 좋다.

1. [workflow_names.py](/D:/workspace/ai-music-video/src/ai_mv/core/workflow_names.py)
2. [doctor_checks.py](/D:/workspace/ai-music-video/src/ai_mv/infra/doctor_checks.py)
3. [config_defaults.py](/D:/workspace/ai-music-video/src/ai_mv/core/orchestration/config_defaults.py)
4. `bootstrap`/`preflight`/entrypoint 영향 파일 수정
5. [pipeline.py](/D:/workspace/ai-music-video/src/ai_mv/core/orchestration/pipeline.py)
6. 새 stage skeleton 5개 추가
7. [input_gate.py](/D:/workspace/ai-music-video/src/ai_mv/core/orchestration/input_gate.py) 최소 수정
8. artifact 최소 생존선 정리
9. [citypop_bible.py](/D:/workspace/ai-music-video/src/ai_mv/presets/citypop_bible.py) 추가
10. `i2v` 기준 mapper/runner 추가
11. `assemble` 단순판 추가
12. M1 테스트 작성

M1 필수 산출물만 남긴 구현 원칙:

- shot별 `Qwen still` 생성
- shot별 `LTX i2v` clip 생성
- `final_mv.mp4` 생성
- `review_report.json` 생성

M1에서 의도적으로 미루는 것:

- `master still`
- `transition still`
- `ia2v`
- `flf2v`
- 복잡한 schema 분리
- 고도화된 rerender policy

## 8. PM Review 포인트

이 문서를 PM 관점에서 다시 볼 때는 아래만 체크하면 된다.

- 교체 시작점 3개가 충분히 작고 명확한가
- 삭제 조건이 “새 skeleton runnable”과 연결되어 있는가
- 유지 대상이 실제로 재사용 가치가 있는가
- 새로 만들 파일 수가 마일스톤 범위를 넘지 않는가
- 테스트 교체 순서가 구현 순서와 맞물리는가
