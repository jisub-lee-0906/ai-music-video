# Legacy Deletion Plan

## 1. 삭제 원칙

이번 재구축은 호환 레이어를 오래 끌고 가면 실패한다.

원칙:

- 실행 경로에서 `Flux/WAN`을 완전히 제거한다.
- profile/director brief를 제거한다.
- 범용 planning 계층을 제거한다.
- 결과물 기준 새 계약이 생기기 전까지는 레거시 코드를 되살리지 않는다.

## 2. 즉시 삭제 대상

아래는 새 구조와 철학이 직접 충돌하므로 우선 삭제 후보다.

문서:

- `docs/pipeline-overview.md`
- `docs/model-prompting-playbook.md`

workflow:

- `workflows/image_flux2.json`
- `workflows/image_flux2_text_to_image.json`
- `workflows/video_wan2_2_14B_flf2v.json`

engine:

- `src/ai_mv/engines/flux_2_dev_ref/`
- `src/ai_mv/engines/flux_2_dev_tti/`
- `src/ai_mv/engines/wan_2_2_flf2v/`
- `src/ai_mv/engines/director_plan/`
- `src/ai_mv/engines/lyrics_timeline/`
- `src/ai_mv/engines/render_plan/`
- `src/ai_mv/engines/scene_plan/`

stage:

- `src/ai_mv/core/stages/flux2_ref_chain.py`
- `src/ai_mv/core/stages/keyframes.py`
- `src/ai_mv/core/stages/lyrics_timeline.py`
- `src/ai_mv/core/stages/director_plan.py`
- `src/ai_mv/core/stages/render_plan.py`
- `src/ai_mv/core/stages/render_verbalizer.py`
- `src/ai_mv/core/stages/scene_plan.py`
- `src/ai_mv/core/stages/storyboard.py`
- `src/ai_mv/core/stages/tti_anchor.py`
- `src/ai_mv/core/stages/wan_interpolation.py`

entrypoint:

- `src/ai_mv/entrypoints/ref_probe.py`
- `src/ai_mv/entrypoints/ref_probe_batch.py`
- `src/ai_mv/entrypoints/tti.py`

## 3. 계약 재작성 후 삭제 대상

아래는 새 계약을 먼저 만든 뒤 제거한다.

core:

- `src/ai_mv/core/director_brief.py`
- `src/ai_mv/core/prompt_digests.py`
- `src/ai_mv/core/quality_review.py`
- `src/ai_mv/core/quality_review_metrics.py`

contracts:

- `src/ai_mv/core/contracts/prompt_normalize.py`
- `src/ai_mv/core/contracts/prompt_schema.py`
- `src/ai_mv/core/contracts/visual_plan_normalize.py`
- `src/ai_mv/core/contracts/visual_plan_schema.py`

stages:

- `src/ai_mv/core/stages/media_resolver.py`
- `src/ai_mv/core/stages/merge_mux.py`
  단, ffmpeg 유틸이 재사용되는지 확인 후 정리

## 4. 우선 보류 대상

아래는 새 파이프라인에서도 재사용 가능성이 높아서 당장 지우지 않는다.

- `src/ai_mv/core/stages/ffmpeg_muxer.py`
- `src/ai_mv/core/stages/acestep_music.py`
- `src/ai_mv/infra/comfy_client.py`
- `src/ai_mv/infra/comfy_local.py`
- `src/ai_mv/infra/comfy_outputs.py`
- `src/ai_mv/infra/comfy_transport.py`
- `src/ai_mv/infra/workflow_patcher.py`
- `src/ai_mv/core/orchestration/stage_runs.py`
- `src/ai_mv/core/state/`
- `src/ai_mv/utils/`

## 5. 테스트 삭제 목록

아래 테스트는 레거시 의미모델과 직접 결합되어 있으므로 제거 대상이다.

- `tests/unit/test_director_brief.py`
- `tests/unit/test_flux_2_dev_ref_chain_runner.py`
- `tests/unit/test_flux_2_dev_ref_runner.py`
- `tests/unit/test_flux_2_dev_tti_runner.py`
- `tests/unit/test_lyrics_timeline_prompt.py`
- `tests/unit/test_prompt_normalize.py`
- `tests/unit/test_render_verbalizer.py`
- `tests/unit/test_visual_planners.py`
- `tests/unit/test_media_resolver.py`
- `tests/unit/test_quality_review.py`

수정 대상:

- `tests/unit/test_pipeline.py`
- `tests/integration/test_pipeline_smoke.py`
- `tests/unit/test_doctor_checks.py`
- `tests/unit/test_bootstrap.py`
- `tests/unit/test_mappers.py`

## 6. 실제 제거 순서

1. 새 문서 작성
2. `workflow_names.py`와 `doctor_checks.py`를 새 workflow 기준으로 수정
3. `pipeline.py`를 새 stage 기준으로 수정
4. 새 stage skeleton 추가
5. 새 engine skeleton 추가
6. 레거시 import 제거
7. 레거시 테스트 제거
8. 레거시 파일 삭제

전환 일정 기준:

- `Doc Freeze`
  문서 기준이 잠긴 시점부터 새 요구사항은 문서 수정 후에만 반영한다.

- `Legacy Freeze`
  새 pipeline skeleton이 들어간 뒤부터는 기존 `Flux/WAN` 경로에 기능 추가를 금지한다.

- `Legacy Cutoff`
  M1 sample run이 통과하고 최소 품질 게이트가 충족되면 기존 `Flux/WAN` 실행 경로를 완전히 삭제한다.

- `Release Gate`
  M2 또는 목표 MVP 기준 테스트가 통과하기 전까지는 전곡 렌더를 공식 지원으로 간주하지 않는다.

## 7. 삭제 체크리스트

아래가 모두 참이면 레거시 삭제를 완료한 것으로 본다.

- `rg "flux|wan|tti|director_brief|storyboard"` 결과가 새 문서 외 실행 코드에서 사라진다.
- `workflows/`에 새 5개 workflow만 남는다.
- `pipeline.py`가 새 6 stage만 호출한다.
- 새 테스트가 통과한다.
- sample run에서 `final_mv.mp4`가 생성된다.

## 8. 작업 방식

삭제는 한 번에 무식하게 하기보다 아래 방식으로 간다.

- 먼저 문서로 기준 잠금
- 다음으로 실행 경로 교체
- 그 다음 테스트 교체
- 마지막에 파일 삭제

이 순서를 어기면 중간에 import 에러와 책임 혼재가 커진다.

리스크 관리:

- 새 skeleton이 runnable 하기 전에는 ffmpeg, Comfy transport, state store 같은 공용 기반은 유지한다.
- `Flux/WAN` 코드 삭제는 “문서 작성 완료”가 아니라 “M1 sample run 통과 + 최소 품질 게이트 통과”를 기준으로 한다.
- 테스트 공백 기간을 만들지 않기 위해 새 테스트를 추가한 뒤 레거시 테스트를 제거한다.

최소 품질 게이트:

- `final_mv.mp4` 생성 성공
- `review_report.json` 생성 성공
- audio/video drift `<= 0.3s`
- 수동 검수 blocking 항목 3개 통과
