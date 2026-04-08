# Citypop MV Rebuild Docs

이 폴더는 기존 범용 `Flux/WAN` 파이프라인을 폐기하고, `ACE-Step 1.5 + Qwen-Image + LTX 2.3 + ffmpeg` 기반의 시티팝 전용 뮤직비디오 파이프라인으로 재구축하기 위한 기준 문서만 담는다.

문서 순서:

1. [citypop-mv-master-plan.md](/D:/workspace/ai-music-video/docs/citypop-mv-master-plan.md)
제품 목표, 고정 철학, stage 구성, 최종 MVP 범위

2. [workflow-usage.md](/D:/workspace/ai-music-video/docs/workflow-usage.md)
현재 채택한 5개 workflow를 어떤 입력/출력 계약으로 사용할지 정리

3. [repo-restructure.md](/D:/workspace/ai-music-video/docs/repo-restructure.md)
새 디렉터리 구조, 모듈 책임, 단계별 구현 순서

4. [legacy-deletion-plan.md](/D:/workspace/ai-music-video/docs/legacy-deletion-plan.md)
삭제 대상, 보류 대상, 제거 순서, 완료 기준

5. [workflow-binding-notes.md](/D:/workspace/ai-music-video/docs/workflow-binding-notes.md)
workflow JSON을 수정하지 않고 mapper에서 어떤 node/input만 바인딩할지 정리

6. [m1-implementation-spec.md](/D:/workspace/ai-music-video/docs/m1-implementation-spec.md)
M1 최소 구현 범위, path 규칙, review 최소 계약

7. [m2-ia2v-spec.md](/D:/workspace/ai-music-video/docs/m2-ia2v-spec.md)
`ia2v` 샷 선정, audio trim, fallback 규칙

8. [m3-flf2v-spec.md](/D:/workspace/ai-music-video/docs/m3-flf2v-spec.md)
`flf2v` 브리지 선정과 입력/검수 규칙

운영 원칙:

- 범용성보다 결과물 일관성을 우선한다.
- 프로필 시스템은 제거한다.
- 스타일은 항상 일본 80~90년대 시티팝으로 고정한다.
- 코드의 역할은 실행, 구조, 검수이며 미학 문장 보정은 LLM draft/polish에 맡긴다.
- 검수 기준은 prompt가 아니라 실제 생성된 이미지와 비디오 결과물이다.
