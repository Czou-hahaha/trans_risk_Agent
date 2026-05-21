import { cn } from "@/lib/utils";

const styles: Record<string, string> = {
  running: "bg-amber-50 text-amber-800 border-amber-200",
  completed: "bg-emerald-50 text-emerald-800 border-emerald-200",
  failed: "bg-red-50 text-red-800 border-red-200",
  pending: "bg-slate-50 text-slate-600 border-slate-200",
  skipped: "bg-slate-50 text-slate-500 border-slate-200",
  unstable: "bg-red-50 text-red-800 border-red-200",
  deteriorating: "bg-orange-50 text-orange-800 border-orange-200",
  watchlist: "bg-amber-50 text-amber-800 border-amber-200",
  healthy: "bg-emerald-50 text-emerald-800 border-emerald-200",
  highly_effective: "bg-emerald-50 text-emerald-800 border-emerald-200",
  effective: "bg-blue-50 text-blue-800 border-blue-200",
  over_tightened: "bg-orange-50 text-orange-800 border-orange-200",
  ineffective: "bg-red-50 text-red-800 border-red-200",
  neutral: "bg-slate-50 text-slate-600 border-slate-200",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium capitalize",
        styles[status] || styles.pending
      )}
    >
      {status}
    </span>
  );
}
