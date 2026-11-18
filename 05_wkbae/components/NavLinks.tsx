'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const ITEMS = [
  { href: '/goals', label: '목표', prefixes: ['/goals', '/weeks'] },
  { href: '/tasks', label: '기간별 보기', prefixes: ['/tasks'] },
  { href: '/summary', label: '달성 현황', prefixes: ['/summary'] },
];

function isUnder(pathname: string, prefix: string) {
  return pathname === prefix || pathname.startsWith(`${prefix}/`);
}

export function NavLinks() {
  const pathname = usePathname();

  return (
    <nav className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3 text-sm font-medium">
      <Link
        href="/"
        aria-current={pathname === '/' ? 'page' : undefined}
        className={`border-b-2 py-1 text-base font-bold text-indigo-700 ${
          pathname === '/' ? 'border-indigo-600' : 'border-transparent'
        }`}
      >
        할 일 관리
      </Link>
      {ITEMS.map(({ href, label, prefixes }) => {
        const active = prefixes.some((prefix) => isUnder(pathname, prefix));
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? 'page' : undefined}
            className={`border-b-2 py-1 ${
              active
                ? 'border-indigo-600 text-indigo-700'
                : 'border-transparent text-slate-600 hover:text-slate-900'
            }`}
          >
            {label}
          </Link>
        );
      })}
    </nav>
  );
}
