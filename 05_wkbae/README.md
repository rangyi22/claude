# 할 일 관리 앱

일일 할 일을 주간 계획과 1년 목표에 연결하고, 칸반 보드에서 상태를 바꾸면 주간·연간 진행률에 자동 반영되는 단일 사용자 웹 앱입니다. 요구사항은 `docs/PRD.md`, 구현 계획은 `docs/PLAN.md`에 있습니다.

## 실행

Node.js와 Docker가 필요합니다.

```bash
npm install
cp .env.example .env.local
docker compose up -d
npm run dev
```

브라우저에서 <http://localhost:3000>을 엽니다. 인증이 없으므로 로컬에서만 실행하세요.

## 검증

```bash
npm run lint
npm run typecheck
npm test                      # 단위·API 통합 테스트 (인메모리 MongoDB)
npx playwright install chromium
npm run test:e2e              # E2E
npm run build && npm run perf # 할 일 1,000개 성능 측정
```

## 구조

| 경로               | 역할                         |
| ------------------ | ---------------------------- |
| `app/`             | 화면과 API Route Handler     |
| `components/`      | 보드, 폼, 진행 바            |
| `lib/repo/`        | MongoDB 저장소와 계층 규칙   |
| `lib/moveQueue.ts` | 카드별 순차 저장과 실패 처리 |
| `tests/`, `e2e/`   | 단위·통합 테스트, E2E        |
