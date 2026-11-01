'use client';

import { useState, type FormEvent, type ReactNode } from 'react';

interface ModalProps {
  title: string;
  submitLabel: string;
  danger?: boolean;
  onClose: () => void;
  onSubmit: (data: FormData) => Promise<void>;
  children: ReactNode;
}

export function Modal({ title, submitLabel, danger, onClose, onSubmit, children }: ModalProps) {
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      await onSubmit(new FormData(event.currentTarget));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : '요청을 처리하지 못했습니다.');
      setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-20 flex items-center justify-center bg-slate-900/40 p-4">
      <form
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onSubmit={handleSubmit}
        className="flex w-full max-w-md flex-col gap-4 rounded-lg bg-white p-6 shadow-lg"
      >
        <h2 className="text-lg font-bold">{title}</h2>
        {children}
        {error && (
          <p role="alert" className="text-sm text-red-700">
            {error}
          </p>
        )}
        <div className="flex justify-end gap-2">
          <button type="button" className="btn" onClick={onClose}>
            취소
          </button>
          <button type="submit" className={danger ? 'btn-danger' : 'btn-primary'} disabled={busy}>
            {submitLabel}
          </button>
        </div>
      </form>
    </div>
  );
}
