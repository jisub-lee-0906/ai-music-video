# M2 IA2V Spec

이 문서는 `LTX ia2v`를 도입하는 M2 확장 명세다.

범위:

- chorus/performance shot에 `ia2v` 추가

비범위:

- `flf2v`
- 전곡 전체를 ia2v로 처리

## 1. IA2V를 쓰는 조건

M2에서 `ia2v` 허용 조건:

- `section_type=chorus`
- `visual_mode=chorus_performance`
- 샷 길이 `4`에서 `8`초

M2 제한:

- 곡당 `ia2v` 샷 최대 `2`
- chorus 하나당 `ia2v` 샷 최대 `1`

## 2. Audio Extraction Rule

`ia2v`는 shot 단위 오디오 추출이 핵심이다.

필수 필드:

- `audio_start_sec`
- `audio_duration_sec`

추출 원칙:

- shot의 `start_sec`, `duration_sec`를 그대로 사용
- 가능하면 bar boundary에 맞춘다
- 너무 짧으면 사용 금지

안전 규칙:

- `audio_duration_sec < 3.0`이면 `ia2v` 금지
- `audio_duration_sec > 8.0`이면 분할 또는 `i2v` fallback

권장 규칙:

- chorus 시작 직후보다 1~2 bar 안정화 이후 구간 우선
- 보컬과 리듬이 명확한 구간 우선

## 3. Selection Rule

`ia2v` shot 선정 순서:

1. chorus section 찾기
2. chorus 내부에서 가장 안정적인 4~6초 구간 선택
3. 해당 shot을 `render_mode=ia2v`로 지정
4. 나머지 chorus shot은 `i2v` 유지

fallback:

- chorus 경계가 불안정하면 `i2v`로 강등
- 오디오 trim 실패 시 `i2v` fallback

## 4. Prompt Rule

`ia2v` prompt seed 문체:

- 장문 자연어 지시형
- `scene`
- `character`
- `action`
- `camera`

필수 요소:

- 퍼포먼스 동작
- 음악 반응 또는 리듬감
- 카메라 제약

금지:

- lip sync를 과도하게 강제하는 표현
- 대사 중심 shot
- 브리지/전환 shot 용도 혼합

## 5. Audio Trim Binding

workflow에서 고정할 노드:

- `LoadAudio`
- `TrimAudioDuration`
- `Duration`

코드가 바인딩할 값:

- source audio path
- trim start
- trim duration

## 6. Review Rule

`ia2v` shot 검수 항목:

- audio reaction feels aligned
- motion is stable
- chorus energy is present
- no obvious desync

rerender target 조건:

- 오디오 반응이 약함
- desync 의심
- 퍼포먼스 shot인데 정적 shot처럼 보임

## 7. Required Tests

- `test_m2_ia2v_gate.py`
- `test_audio_trim_mapping.py`
- `test_ia2v_fallback_to_i2v.py`

## 8. Exit Criteria

- chorus shot 최소 1개가 `ia2v`로 생성
- trim audio가 올바른 길이로 들어감
- obvious desync 없음
