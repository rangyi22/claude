import { spawn } from 'node:child_process';
import { MongoMemoryServer } from 'mongodb-memory-server';

export interface TestServer {
  uri: string;
  stop: () => Promise<void>;
}

export async function waitForServer(baseUrl: string): Promise<void> {
  for (let attempt = 0; attempt < 100; attempt += 1) {
    if ((await fetch(`${baseUrl}/api/goals`).catch(() => null))?.ok) return;
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
  throw new Error('서버가 시작되지 않았습니다.');
}

/** 인메모리 MongoDB에 붙은 프로덕션 빌드 서버를 띄운다. `next build`가 먼저 끝나 있어야 한다. */
export async function startTestServer(port: number): Promise<TestServer> {
  const mongo = await MongoMemoryServer.create();
  const uri = mongo.getUri();
  const next = spawn('node_modules/.bin/next', ['start', '-p', String(port)], {
    env: { ...process.env, MONGODB_URI: uri, MONGODB_DB: 'todo_test' },
    stdio: 'inherit',
  });
  return {
    uri,
    async stop() {
      next.kill();
      await mongo.stop();
    },
  };
}
