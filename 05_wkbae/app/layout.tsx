import type { Metadata } from 'next';
import Link from 'next/link';
import type { ReactNode } from 'react';
import './globals.css';

export const metadata: Metadata = {
  title: '할 일 관리',
  description: '일일 할 일을 주간 계획과 1년 목표에 연결해 관리합니다.',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-slate-100 text-slate-900">
        <header className="border-b border-slate-200 bg-white">
          <nav className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3 text-sm font-medium">
            <Link href="/" className="text-base font-bold text-indigo-700">
              할 일 관리
            </Link>
            <Link href="/">목표</Link>
            <Link href="/tasks">기간별 보기</Link>
            <Link href="/summary">달성 현황</Link>
          </nav>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
      </body>
    </html>
  );
}
