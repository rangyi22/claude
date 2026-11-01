'use client';

import {
  closestCenter,
  DndContext,
  KeyboardCode,
  KeyboardSensor,
  PointerSensor,
  useDraggable,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
  type KeyboardCoordinateGetter,
} from '@dnd-kit/core';
import type { Task, TaskStatus } from '@/lib/types';

const COLUMNS: { status: TaskStatus; label: string }[] = [
  { status: 'todo', label: '할 일' },
  { status: 'doing', label: '진행 중' },
  { status: 'done', label: '완료' },
];

function moveByColumn(
  event: KeyboardEvent,
  { context, currentCoordinates }: Parameters<KeyboardCoordinateGetter>[1],
) {
  const direction = { [KeyboardCode.Right]: 1, [KeyboardCode.Left]: -1 }[event.code];
  if (!direction) return undefined;
  event.preventDefault();
  const lefts = [...context.droppableRects.values()].map((rect) => rect.left).sort((a, b) => a - b);
  const step = lefts.length > 1 ? lefts[1] - lefts[0] : 0;
  return { ...currentCoordinates, x: currentCoordinates.x + direction * step };
}

interface CardProps {
  task: Task;
  onEdit: (task: Task) => void;
  onDelete: (task: Task) => void;
}

function Card({ task, onEdit, onDelete }: CardProps) {
  const { attributes, listeners, setNodeRef, setActivatorNodeRef, transform, isDragging } =
    useDraggable({ id: task.id });

  return (
    <li
      ref={(node) => {
        setNodeRef(node);
        setActivatorNodeRef(node);
      }}
      {...attributes}
      {...listeners}
      data-testid="task-card"
      aria-label={`${task.title}, 가중치 ${task.weight}`}
      style={transform ? { transform: `translate(${transform.x}px, ${transform.y}px)` } : undefined}
      className={`cursor-grab rounded-md border border-slate-200 bg-white p-3 shadow-sm ${
        isDragging ? 'relative z-10 opacity-80 shadow-lg' : ''
      }`}
    >
      <p className="text-sm font-medium">{task.title}</p>
      <div className="mt-2 flex items-center justify-between text-sm text-slate-500">
        <span>
          {task.date} · 가중치 {task.weight}
        </span>
        <span className="flex gap-2">
          <button type="button" className="hover:underline" onClick={() => onEdit(task)}>
            수정
          </button>
          <button
            type="button"
            className="text-red-700 hover:underline"
            onClick={() => onDelete(task)}
          >
            삭제
          </button>
        </span>
      </div>
    </li>
  );
}

interface ColumnProps extends Omit<CardProps, 'task'> {
  status: TaskStatus;
  label: string;
  tasks: Task[];
}

function Column({ status, label, tasks, onEdit, onDelete }: ColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id: status });

  return (
    <section
      ref={setNodeRef}
      data-testid={`column-${status}`}
      aria-label={label}
      className={`min-h-64 rounded-lg p-3 ${isOver ? 'bg-indigo-100' : 'bg-slate-200'}`}
    >
      <h2 className="mb-3 text-sm font-bold text-slate-700">
        {label} <span className="font-normal">({tasks.length})</span>
      </h2>
      <ul className="flex flex-col gap-2">
        {tasks.map((task) => (
          <Card key={task.id} task={task} onEdit={onEdit} onDelete={onDelete} />
        ))}
      </ul>
    </section>
  );
}

interface BoardProps extends Omit<CardProps, 'task'> {
  tasks: Task[];
  onMove: (task: Task, status: TaskStatus) => void;
}

export function Board({ tasks, onMove, onEdit, onDelete }: BoardProps) {
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: moveByColumn }),
  );

  function handleDragEnd({ active, over }: DragEndEvent) {
    const task = tasks.find((candidate) => candidate.id === active.id);
    const status = over?.id as TaskStatus | undefined;
    if (task && status && status !== task.status) onMove(task, status);
  }

  return (
    <DndContext
      id="task-board"
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
      accessibility={{
        screenReaderInstructions: {
          draggable: '스페이스 키로 카드를 들고, 좌우 방향키로 옮긴 뒤 스페이스 키로 놓습니다.',
        },
      }}
    >
      <div className="grid grid-cols-3 gap-4">
        {COLUMNS.map((column) => (
          <Column
            key={column.status}
            {...column}
            tasks={tasks
              .filter((task) => task.status === column.status)
              .sort((a, b) => a.order - b.order)}
            onEdit={onEdit}
            onDelete={onDelete}
          />
        ))}
      </div>
    </DndContext>
  );
}
