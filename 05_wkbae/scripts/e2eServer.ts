import { startTestServer } from './testServer';

async function main() {
  const server = await startTestServer(3100);
  process.on('SIGTERM', () => void server.stop().then(() => process.exit(0)));
}

void main();
