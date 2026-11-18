# 할 일 관리 앱

일일 할 일을 주간 계획과 Schedule(1년 목표)에 연결하고, 월간 계획도 함께 관리하며, 칸반 보드에서 상태를 바꾸면 진행률에 자동 반영되는 단일 사용자 웹 앱입니다. 요구사항은 `docs/PRD.md`, 구현 계획은 `docs/PLAN.md`에 있습니다.

## 실행

Node.js와 Docker가 필요합니다.

```bash
npm install
cp .env.example .env.local
docker compose up -d
npm run dev
```

브라우저에서 <http://localhost:3000>을 엽니다. 인증이 없으므로 로컬에서만 실행하세요.

## MongoDB Atlas 사용

로컬 Docker 대신 Atlas에 저장하려면 `.env.local`을 아래처럼 바꿉니다. 비밀번호가 들어가므로 이 파일은 git에 올리지 않습니다.

```bash
MONGODB_URI=mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGODB_DB=todoapp
```

- Atlas의 Database Access에서 사용자를 만들고, Network Access에서 접속하는 IP를 허용해야 합니다.
- 앱이 처음 연결하거나 `npm run db:init`을 실행하면 `todoapp` 데이터베이스에 `goals`, `weeks`, `months`, `tasks` 컬렉션과 인덱스가 만들어집니다. 데이터가 없어도 Atlas의 Data Explorer에서 바로 보입니다.
- 데이터베이스 이름은 `MONGODB_DB`로 정하며 기본값은 `todoapp`입니다. 이름이 다르면(예: 예전 `todo_app`) 별도 데이터베이스이므로 기존 데이터는 옮겨 가지 않습니다.

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
