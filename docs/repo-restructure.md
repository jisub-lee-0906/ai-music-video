# Repository Restructure Plan

## 1. 목표

현재 저장소는 범용 planning과 `Flux/WAN` 중심 구조라서 새 파이프라인과 맞지 않는다.

새 구조의 목표:

- stage 이름과 코드 책임이 실제 workflow와 일치해야 한다.
- profile/director brief 의존을 제거해야 한다.
- shot plan과 render plan이 시티팝 고정 규칙을 직접 소비해야 한다.
- 결과물 검수와 재생성 루프를 중심에 둬야 한다.

## 2. 권장 디렉터리 구조

권장 구조:

```text
src/ai_mv/
  cli/
  core/
    artifacts/
    contracts/
    orchestration/
    stages/
  engines/
    acestep_audio/
    citypop_plan/
    qwen_stills/
    ltx_i2v/
    ltx_ia2v/
    ltx_flf2v/
    review/
  infra/
  utils/
  presets/
    citypop_bible.py
```

## 3. 새 stage 파일

남길 것:

- `ffmpeg_muxer.py`
- `acestep_music.py`
  단, 내부 계약은 새 구조에 맞게 수정

새로 만들 것:

- `plan_citypop_mv.py`
- `render_stills.py`
- `render_clips.py`
- `assemble_mv.py`
- `review_outputs.py`

역할:

### `plan_citypop_mv.py`

- `music_map`을 읽어 shot plan 생성
- section 기반 visual mode 결정
- render mode 결정
- draft/polish 대상 prompt seed 생성

### `render_stills.py`

- Qwen still generation orchestration
- master still과 shot still 생성
- still 산출물 manifest 작성

### `render_clips.py`

- shot별 mode에 맞춰 `i2v`, `ia2v`, `flf2v` runner 호출
- shot 단위 audio trim
- clip 결과 기록

### `assemble_mv.py`

- shot clip ordering
- hold 삽입
- concat/mux
- final output manifest 작성

### `review_outputs.py`

- still/clip/final video를 대상으로 review signal 생성
- rerender list 작성

## 4. 새 engine 파일

권장 엔진 구조:

```text
src/ai_mv/engines/
  acestep_audio/
    mapper.py
    planner.py
    runner.py
  citypop_plan/
    planner.py
    shot_rules.py
    prompting.py
  qwen_stills/
    mapper.py
    runner.py
  ltx_i2v/
    mapper.py
    runner.py
  ltx_ia2v/
    mapper.py
    runner.py
  ltx_flf2v/
    mapper.py
    runner.py
  review/
    planner.py
    metrics.py
```

## 5. 새 orchestration 구조

`pipeline.py`의 ordered stages는 아래로 교체한다.

```text
audio
plan
stills
clips
assemble
review
```

payload 핵심 키:

- `music_plan`
- `music_map`
- `citypop_bible`
- `shot_plan`
- `render_plan`
- `still_results`
- `clip_results`
- `final_video`
- `review_report`

삭제할 payload 키:

- `story_profile`
- `lyrics_timeline`
- `scene_outline`
- `direction_plan`
- `prompt_plan.ref_items`
- `prompt_plan.wan_items`
- `flux2_ref_images`
- `clip_routes`

## 6. presets 계층

새로 추가할 정적 계층:

- [citypop_bible.py](/D:/workspace/ai-music-video/src/ai_mv/presets/citypop_bible.py)

담을 내용:

- palette
- motifs
- negative rules
- section별 visual defaults
- shot role defaults
- prompt seed fragments

이 파일은 기존 profile을 대체한다.

## 7. 문서와 테스트 구조

문서는 이 순서로 유지한다.

- 제품 정의
- workflow 활용
- 구조 개편
- 삭제 계획

테스트도 새 구조에 맞춰 재편한다.

권장 테스트 묶음:

- `test_citypop_plan.py`
- `test_qwen_stills_mapper.py`
- `test_ltx_i2v_mapper.py`
- `test_ltx_ia2v_mapper.py`
- `test_ltx_flf2v_mapper.py`
- `test_pipeline_v2.py`
- `test_review_outputs.py`

## 8. 구현 순서

1. `workflow_names.py` 교체
2. `pipeline.py` stage 순서 교체
3. 새 stage skeleton 추가
4. `citypop_bible` 추가
5. `plan` 구현
6. `qwen_stills` 구현
7. `ltx_i2v` 구현
8. `assemble` 구현
9. `review` 구현
10. `ia2v`, `flf2v` 확장

각 단계 완료 산출물:

- 문서 잠금
  `docs/`에 제품 정의, workflow 활용, 구조 개편, 삭제 계획이 최신 상태로 반영됨

- pipeline skeleton
  새 6 stage가 import 에러 없이 연결되고, 더미 payload로 end-to-end 테스트 가능

- Qwen stills
  shot별 still 파일과 manifest가 생성됨

- LTX clips
  shot별 clip 파일과 clip manifest가 생성됨

- review loop
  review report가 rerender target을 반환함

운영 체크포인트:

- Checkpoint A
  새 pipeline 이름과 payload 키가 잠김
  검증 방식: 문서 검토 + unit test에서 새 stage 이름과 payload key 확인

- Checkpoint B
  M1 runnable sample 생성 성공
  검증 방식: `pytest` smoke + 샘플 CLI run + 산출물 존재 확인

- Checkpoint C
  M2 `ia2v` 샷 추가 성공
  검증 방식: routing unit test + 샘플 run에서 chorus shot 확인

- Checkpoint D
  M3 `flf2v` 브리지 추가 성공
  검증 방식: routing unit test + 샘플 run에서 bridge shot 확인

## 9. 브랜치 운영 방식

작업 브랜치는 기능별로 나누는 게 좋다.

- `codex/rebuild-docs`
- `codex/rebuild-pipeline-skeleton`
- `codex/rebuild-qwen-stills`
- `codex/rebuild-ltx-clips`
- `codex/rebuild-review-loop`

문서 작업 후 바로 해야 할 첫 구현 브랜치:

- `codex/rebuild-pipeline-skeleton`
