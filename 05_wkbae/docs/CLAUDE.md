## 참고 문서
- PRD: docs/PRD.md
- 구현 계획: docs/PLAN.md

작업 전 반드시 위 문서를 읽고 시작할 것

## 스택

Next.js App Router, TypeScript, Tailwind CSS, MongoDB 공식 드라이버, zod, @dnd-kit/core, Vitest, Playwright.

## 명령어

- 개발: `docker compose up -d` 후 `npm run dev`
- 검사: `npm run lint`, `npm run typecheck`, `npm run build`
- 테스트: `npm test`, `npm run test:e2e`
- 성능: `npm run build && npm run perf`

## 규칙

- 진행률은 저장하지 않는다. `lib/progress.ts`의 `calcProgress`로 조회 시 계산한다.
- 모든 쿼리는 `userId: USER_ID`로 거른다.
- 날짜는 `YYYY-MM-DD` 문자열로 저장하고 비교한다.
- 하위가 있는 목표·주간 계획은 삭제하지 않고 409를 반환한다.
- 할 일 날짜는 연결된 주간 계획 기간 안이어야 한다.
- 카드 이동 저장은 `lib/moveQueue.ts`를 거친다. 처리 중에 받은 조회 응답은 화면에 반영하지 않는다.
- 함수는 선언문으로 쓴다(`func-style`). `console`은 쓰지 않는다.