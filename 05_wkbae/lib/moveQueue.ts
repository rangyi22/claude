import type { TaskStatus } from './types';

interface MoveQueueOptions<R> {
  send: (id: string, status: TaskStatus) => Promise<R>;
  onSuccess: (result: R) => void;
  /** 실패한 카드의 마지막 확정 상태를 넘긴다. 대기 중이던 같은 카드의 이동은 버린다. */
  onFailure: (id: string, confirmed: TaskStatus, error: unknown) => void;
  /** 처리 중인 이동이 하나도 남지 않았을 때 호출한다. */
  onIdle: () => void;
}

export interface MoveQueue {
  enqueue: (id: string, from: TaskStatus, to: TaskStatus) => void;
  isBusy: () => boolean;
}

interface CardState {
  confirmed: TaskStatus;
  pending: TaskStatus[];
}

/** 카드별로 요청을 한 번에 하나씩 보내, 늦은 응답이 최신 상태를 덮어쓰지 않게 한다. */
export function createMoveQueue<R>(options: MoveQueueOptions<R>): MoveQueue {
  const cards = new Map<string, CardState>();

  async function drain(id: string, card: CardState): Promise<void> {
    while (card.pending.length > 0) {
      const status = card.pending[0];
      try {
        const result = await options.send(id, status);
        card.pending.shift();
        card.confirmed = status;
        options.onSuccess(result);
      } catch (error) {
        card.pending = [];
        options.onFailure(id, card.confirmed, error);
      }
    }
    cards.delete(id);
    if (cards.size === 0) options.onIdle();
  }

  return {
    enqueue(id, from, to) {
      const card = cards.get(id);
      if (card) {
        card.pending.push(to);
        return;
      }
      const created = { confirmed: from, pending: [to] };
      cards.set(id, created);
      void drain(id, created);
    },
    isBusy: () => cards.size > 0,
  };
}
