# Workflow Usage Plan

이 문서는 현재 저장소에 남긴 6개 workflow를 어떤 역할로 사용할지 고정한다.

채택 workflow:

- [audio_ace_step_1_5_split_4b.json](/D:/workspace/ai-music-video/workflows/audio_ace_step_1_5_split_4b.json)
- [image_flux2_text_to_image.json](/D:/workspace/ai-music-video/workflows/image_flux2_text_to_image.json)
- [image_flux2.json](/D:/workspace/ai-music-video/workflows/image_flux2.json)
- [video_ltx2_3_i2v.json](/D:/workspace/ai-music-video/workflows/video_ltx2_3_i2v.json)
- [video_ltx2_3_ia2v.json](/D:/workspace/ai-music-video/workflows/video_ltx2_3_ia2v.json)
- [video_ltx2_3_flf2v.json](/D:/workspace/ai-music-video/workflows/video_ltx2_3_flf2v.json)

## 1. ACE-Step 1.5

파일:

- [audio_ace_step_1_5_split_4b.json](/D:/workspace/ai-music-video/workflows/audio_ace_step_1_5_split_4b.json)

역할:

- 곡 생성
- 가사와 tags 입력
- 길이와 bpm 생성 기준 제공
- 후속 shot planning에 필요한 timing source 제공

코드에서 바인딩할 핵심 입력:

- `tags`
- `lyrics`
- `seed`
- `bpm`
- `duration`
- `language`
- `keyscale`

기대 출력:

- `music.mp3`
- 섹션별 길이 추정에 필요한 timing metadata

주의:

- 지금은 split 4b workflow를 기준으로 mapper를 짜야 한다.
- 음악 stage에서 profile 정보를 읽지 않는다.
- 시티팝용 tag/prompt seed는 코드 상수 또는 정적 템플릿으로 관리한다.

## 2. Flux2 still workflows

파일:

- [image_flux2_text_to_image.json](/D:/workspace/ai-music-video/workflows/image_flux2_text_to_image.json)
- [image_flux2.json](/D:/workspace/ai-music-video/workflows/image_flux2.json)

역할:

- 대표 캐릭터 still
- 샷별 base still
- 장소/시간대/무드 variation still

코드에서 바인딩할 핵심 입력:

- positive prompt
- negative prompt
- width
- height
- seed
- filename prefix

생성 전략:

- `master still`
  전체 곡에서 identity reference로 쓰는 대표 이미지

- `shot still`
  각 샷의 직접 입력용 이미지

- `transition still`
  `flf2v`의 first/last frame source로 쓰는 보조 이미지

주의:

- `image_flux2_text_to_image.json`은 기본 still 생성에 사용한다.
- `image_flux2.json`은 기존 still을 reference로 받는 rerender/keyframe refinement에 사용한다.
- Flux2 still stage가 anchor와 shot still 역할을 모두 맡는다.
- prompt seed는 코드가 짧게 만들고, 자연어 품질은 LLM draft/polish로 넘긴다.

## 3. LTX 2.3 `i2v`

파일:

- [video_ltx2_3_i2v.json](/D:/workspace/ai-music-video/workflows/video_ltx2_3_i2v.json)

역할:

- 단일 still을 기반으로 일반 샷 생성
- 가장 기본적인 shot renderer

적용 샷:

- 인트로 mood shot
- 차 안/해변/도시의 단일 상태 샷
- 감정 유지 중심 샷

코드에서 바인딩할 핵심 입력:

- source image
- width
- height
- fps
- frame count
- prompt
- negative prompt
- filename prefix

주의:

- 첫 수직 슬라이스는 이 workflow만으로도 돌아가야 한다.
- `i2v`만으로 15초 샘플을 먼저 완성하고, 그 다음에 `ia2v`, `flf2v`를 붙인다.

## 4. LTX 2.3 `ia2v`

파일:

- [video_ltx2_3_ia2v.json](/D:/workspace/ai-music-video/workflows/video_ltx2_3_ia2v.json)

역할:

- 이미지와 오디오 세그먼트를 같이 써서 음악 반응형 샷 생성

적용 샷:

- 코러스 퍼포먼스
- 보컬 존재감이 큰 샷
- 립싱크까지는 아니더라도 음악 반응이 중요한 샷

코드에서 바인딩할 핵심 입력:

- source image
- trimmed audio segment
- duration
- fps
- frame count
- prompt
- negative prompt
- filename prefix

주의:

- 오디오 segment trim 로직이 필요하다.
- `assemble` stage가 아니라 `clips` stage에서 shot 단위 audio slicing을 끝내야 한다.
- 초기에는 chorus 전용으로 제한하는 것이 좋다.

## 5. LTX 2.3 `flf2v`

파일:

- [video_ltx2_3_flf2v.json](/D:/workspace/ai-music-video/workflows/video_ltx2_3_flf2v.json)

역할:

- 시작 still과 종료 still 사이의 브리지 샷 생성

적용 샷:

- 공간 전환
- 시간대 전환
- 감정 상승 전환
- section bridge

코드에서 바인딩할 핵심 입력:

- first frame image
- last frame image
- duration
- fps
- prompt
- negative prompt
- filename prefix

주의:

- 기존 WAN처럼 인접 pair를 무조건 전부 잇는 모델이 아니다.
- 오직 계획된 bridge shot에만 사용한다.
- `plan` 단계에서 명시적으로 `render_mode=flf2v`인 샷만 생성한다.

## 6. Shot Routing 표준

기본 라우팅 표:

- `visual_mode=profile_mood` -> `i2v`
- `visual_mode=night_drive` -> `i2v`
- `visual_mode=chorus_performance` -> `ia2v`
- `visual_mode=transition_bridge` -> `flf2v`
- `visual_mode=memory_flash` -> `i2v`

최초 구현 시 단순 규칙:

- M1:
  `intro`, `verse`, `prechorus`, `chorus`, `bridge`, `outro` 전부 `i2v`

- M2:
  `chorus`만 `ia2v`, 나머지는 `i2v`

- M3:
  계획된 `transition_bridge`만 `flf2v`, `chorus`는 `ia2v`, 나머지는 `i2v`

초기 구현 금지:

- M1에서 `ia2v`와 `flf2v`를 함께 도입하는 것
- audio-reactive 샷과 bridge 샷을 같은 마일스톤에서 동시에 안정화하려는 것
- mode별 prompt 전략을 동시에 최적화하려는 것

## 7. 프롬프트 처리 원칙

각 workflow 입력 prompt는 3단계만 허용한다.

1. `prompt_seed`
2. `prompt_draft`
3. `prompt_polish`

금지:

- 코드가 주어 문구를 강제 정규화하는 것
- workflow별로 다른 미학 문장을 코드에서 장문으로 덧붙이는 것
- 범용 prompt normalize layer를 크게 유지하는 것

허용:

- workflow에 필요한 필수 제약만 코드로 추가
- negative prompt는 workflow별 고정 규칙으로 관리

## 8. 산출물 규칙

workflow별 산출물 위치:

- `audio`: `artifacts/<run_id>/audio/`
- `stills`: `artifacts/<run_id>/stills/`
- `clips`: `artifacts/<run_id>/clips/`
- `final`: `artifacts/<run_id>/final/`
- `review`: `artifacts/<run_id>/review/`

파일명 규칙:

- shot id 기반
- workflow mode 포함
- 재생성 시 attempt index 포함

예:

- `S003_i2v_a01.mp4`
- `S005_ia2v_a02.mp4`
- `S008_flf2v_a01.mp4`
