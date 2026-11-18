/* eslint-disable no-console -- 준비 결과를 터미널에 출력하는 스크립트다. */
import { closeDb, getDb } from '../lib/db';

/** MONGODB_URI가 가리키는 곳(로컬 또는 Atlas)에 데이터베이스와 컬렉션, 인덱스를 만든다. 여러 번 실행해도 안전하다. */
async function main() {
  const db = await getDb();
  const collections = await db.listCollections({}, { nameOnly: true }).toArray();
  const names = collections.map((collection) => collection.name).sort();
  console.log(`데이터베이스 '${db.databaseName}' 준비 완료: ${names.join(', ')}`);
  await closeDb();
}

main().catch((error: Error) => {
  console.error(`데이터베이스를 준비하지 못했습니다: ${error.message}`);
  process.exitCode = 1;
});
