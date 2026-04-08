# Model Prompting Playbook

이 문서는 프로젝트의 최상위 prompting 기준이다.  
repo 구현이 이 문서와 충돌하면, repo를 고친다.

기준:
- 공식 문서/튜토리얼
- 현재 repo workflow의 실제 text encoder / graph
- 실전 생성 결과물 검수

## 1. Flux 2 Dev TTI

공식 기준:
- ComfyUI Flux 2 Dev 튜토리얼은 `mistral_3_small_flux2_bf16.safetensors` encoder 전제를 둔다.
- 문장형 prompt를 무리 없이 받지만, anchor 목적에서는 정보 분리가 중요하다.

현재 repo workflow:
- [image_flux2_text_to_image.json](/D:/workspace/ai-music-video/workflows/image_flux2_text_to_image.json)
- [image_flux2.json](/D:/workspace/ai-music-video/workflows/image_flux2.json)

프로젝트 역할:
- 캐릭터 anchor 이미지
- 장면 설명이 아니라 캐릭터 정체성 고정

잘 먹히는 형식:
- `anchor_subject`
- `anchor_hair`
- `anchor_top`
- `anchor_bottom`
- `anchor_shoes`
- `anchor_pose`
- `anchor_background`

피해야 할 형식:
- `vocalist`, `idol` 같은 역할 고정
- 배경/행동/무드까지 한 문장에 과도하게 섞기
- 국적/스타일 자동 추론

운영 규칙:
- 캐릭터 정체성은 프로필에서만 온다
- 기본 subject는 짧고, 디테일은 `anchor_*`로 분리한다

## 2. Flux 2 Dev ITI / REF

공식 기준:
- Flux 2 Dev 계열은 문장형 prompt를 잘 받지만, 장면 정보가 많을수록 의미 계층이 분명해야 한다.

현재 repo workflow:
- [flux2_ref_chain.py](/D:/workspace/ai-music-video/src/ai_mv/core/stages/flux2_ref_chain.py)
- [mapper.py](/D:/workspace/ai-music-video/src/ai_mv/engines/flux_2_dev_ref/mapper.py)

프로젝트 역할:
- keyframe 장면 생성

권장 구조:
1. structured shot card
2. LLM full draft
3. LLM polish

REF prompt 목표:
- 현재 장면의 action
- 현재 place
- 물리적 detail
- continuity carry
- framing
- face lock

피해야 할 형식:
- 코드가 `She is ...` 같은 주어 문장을 고정하는 것
- 프로필에 없는 국적/스타일/직업 삽입
- 감정 설명만 길게 쓰는 것
- 이전 REF prompt 복붙

운영 규칙:
- `Keep the face.`는 REF only
- subject wording은 LLM이 최종 선택하되, 구조 의미는 shot card가 제한한다

## 3. ACE-Step 1.5

공식 기준:
- ComfyUI ACE-Step 1.5 가이드는 split workflow와 Qwen text encoder 조합을 전제로 한다.
- 구조와 가사의 역할 분리가 중요하다.

현재 repo workflow:
- [audio_ace_step_1_5_split_4b.json](/D:/workspace/ai-music-video/workflows/audio_ace_step_1_5_split_4b.json)
- local workflow는 공식 예시와 encoder 조합이 다를 수 있다. 실제 workflow 파일이 우선이다.

프로젝트 역할:
- 노래 구조
- 가사
- tags
- timing 출발점

권장 구조:
- outline
- full draft
- targeted rewrite / polish

운영 규칙:
- language는 언어만 뜻한다
- 국적/비주얼을 자동 추론하지 않는다
- 좋은 songform과 lyric 품질은 LLM 단계에서 해결한다

피해야 할 형식:
- 코드가 lyric aesthetics를 직접 강제
- 특정 장르/국가/성별의 숨은 기본값

## 4. WAN 2.2 FLF2V

공식 기준:
- ComfyUI Wan 2.2 튜토리얼은 `umt5_xxl_fp8_e4m3fn_scaled.safetensors` encoder와 FLF2V workflow를 전제로 한다.
- `WanFirstLastFrameToVideo` 기본은 `length=81 frames`이며 workflow-native fps 전제를 존중해야 한다.

현재 repo workflow:
- [video_wan2_2_14B_flf2v.json](/D:/workspace/ai-music-video/workflows/video_wan2_2_14B_flf2v.json)

프로젝트 역할:
- 인접 keyframe 사이 motion bridge

권장 구조:
1. structured pair card
2. LLM full draft
3. LLM polish

WAN prompt 목표:
- 한 개의 clear motion
- 한 개의 continuity detail
- 짧은 전환 설명

피해야 할 형식:
- REF 전체 장면을 다시 설명하는 것
- decorative cinematic filler
- face-lock suffix
- max frame cap으로 workflow-native 길이를 자르는 것

운영 규칙:
- `frames = round(duration_sec * wan_fps)`
- clip length 제약은 upstream segmentation 책임

## 공통 원칙

- 코드는 구조와 검증만 한다
- 코드는 문장 미학을 만들지 않는다
- 프로필이 세계와 캐릭터를 결정한다
- 음악이 timing과 분할을 결정한다
- 가사는 보조 의미층으로만 개입한다
- 품질 향상은 `LLM draft -> LLM polish -> 자동검수`로 해결한다
