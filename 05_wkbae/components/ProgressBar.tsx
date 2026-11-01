export function ProgressBar({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex items-center gap-3">
      <div
        role="progressbar"
        aria-label={label}
        aria-valuenow={value}
        aria-valuemin={0}
        aria-valuemax={100}
        className="h-2 flex-1 overflow-hidden rounded-full bg-slate-200"
      >
        <div className="h-full bg-indigo-600 transition-all" style={{ width: `${value}%` }} />
      </div>
      <span className="w-12 text-right text-sm font-semibold tabular-nums">{value}%</span>
    </div>
  );
}
