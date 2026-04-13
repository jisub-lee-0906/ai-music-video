# M1 Implementation Spec

이 문서는 M1 `First Runnable` 구현에 필요한 최소 명세를 고정한다.

범위:

- `ACE-Step`
- `Qwen stills`
- `LTX i2v`
- `ffmpeg assemble`
- `review report`

비범위:

- `ia2v`
- `flf2v`
- `master still`
- `transition still`
- 고도화된 rerender policy

## 1. 입력

입력 필드:

- `concept_text`
- `duration_sec`
- 선택적 `seed`

입력 제약:

- `duration_sec`는 `15` 이상 `20` 이하
- `concept_text`는 빈 문자열 금지

## 2. Audio Plan

`concept_text`에서 아래를 파생한다.

- `tags`
- `lyrics_seed`
- `bpm_target`
- `keyscale`
- `language`

M1 안전 규칙:

- `lyrics_seed`는 짧은 section 구조만 만든다
- `bpm_target`은 시티팝 안정 구간으로 제한한다
- 복잡한 가사 서사보다 무드와 후렴 반복을 우선한다

## 3. Shot Plan

M1 shot plan 규칙:

- 총 샷 수 `4`에서 `6`
- 모든 샷 `render_mode=i2v`
- 모든 샷은 `shot still` 하나만 사용

section 기반 기본 배치:

- intro: 1 shot
- verse: 1 or 2 shots
- chorus: 1 or 2 shots
- outro: 1 shot

기본 shot duration:

- 짧은 샷: `2.5`에서 `4.0`초
- 긴 샷: `4.0`에서 `6.0`초

shot plan 필수 필드:

- `shot_id`
- `section_name`
- `section_type`
- `start_sec`
- `end_sec`
- `duration_sec`
- `shot_role`
- `visual_mode`
- `render_mode`

M1 acceptance:

- 샷 수가 `4`에서 `6`
- 모든 샷 `render_mode=i2v`
- 전체 shot duration 합이 오디오 길이와 크게 어긋나지 않을 것

## 4. Qwen Stills

M1 규칙:

- 샷마다 still 1장 생성
- `master still` 생성 안 함
- `still_b` 비움

prompt 형식:

- 쉼표 나열형
- `subject, outfit, pose, place, lighting, era texture`

still 실패 시 fallback:

- 동일 shot prompt로 seed만 바꿔 1회 재시도
- 재시도도 실패하면 run fail

## 5. LTX i2v

M1 규칙:

- 모든 샷 `i2v`
- 각 샷은 still 1장만 입력
- prompt seed는 장면 지시형 자연어

frame 계산:

- `frame_count = round(duration_sec * fps)`
- 단, workflow expression이 있으면 primitive 값만 넣고 expression을 유지

기본 fps:

- `24` 또는 `25`
- M1에서는 하나로 고정하는 편이 좋다

## 6. Path Rules

run root:

- `artifacts/<run_id>/`

필수 출력:

- `artifacts/<run_id>/audio/music.mp3`
- `artifacts/<run_id>/stills/<shot_id>.png`
- `artifacts/<run_id>/clips/<shot_id>_i2v.mp4`
- `artifacts/<run_id>/final/final_mv.mp4`
- `artifacts/<run_id>/review/review_report.json`

재시도 파일명:

- still: `<shot_id>_a01.png`, `<shot_id>_a02.png`
- clip: `<shot_id>_i2v_a01.mp4`, `<shot_id>_i2v_a02.mp4`

## 7. Review Report

M1 최소 계약:

- `status`
- `audio_video_drift_sec`
- `blocking_checks`
- `non_blocking_checks`
- `rerender_targets`

`rerender_targets` 생성 규칙:

- still 생성 실패 샷
- clip 생성 실패 샷
- blocking 검수 실패 샷

M1 fail rule:

- `rerender_targets`가 1개 이상이면 run은 provisional fail
- 단, artifact existence test는 별도로 통과 가능

## 8. Required Tests

- `test_m1_sample_run.py`
- `test_release_gate_metrics.py`
- `test_citypop_plan_acceptance.py`
- `test_review_report_contract.py`

## 9. Exit Criteria

M1 완료 조건:

- sample run 1회 end-to-end 통과
- `final_mv.mp4` 생성
- drift `<= 0.3s`
- blocking 검수 통과
