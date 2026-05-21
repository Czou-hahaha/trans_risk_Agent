"use client";

import type { InvestigationEvaluation } from "@/lib/api";

type Props = {
  evaluation: InvestigationEvaluation | null;
  loading?: boolean;
  error?: string | null;
};

function scoreColor(score: number): string {
  if (score >= 0.8) return "text-emerald-700 bg-emerald-50 border-emerald-200";
  if (score >= 0.6) return "text-amber-700 bg-amber-50 border-amber-200";
  return "text-red-700 bg-red-50 border-red-200";
}

function ScoreCard({ label, score }: { label: string; score: number }) {
  const pct = Math.round(score * 100);
  return (
    <div
      className={`rounded-lg border px-3 py-2 ${scoreColor(score)}`}
      title={`${label}: ${pct}%`}
    >
      <p className="text-[10px] font-semibold uppercase tracking-wide opacity-80">
        {label}
      </p>
      <p className="text-lg font-semibold tabular-nums">{pct}%</p>
    </div>
  );
}

export function InvestigationQualityPanel({ evaluation, loading, error }: Props) {
  if (loading) {
    return (
      <section className="rounded-lg border border-surface-border bg-white p-4">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Investigation Quality
        </h2>
        <p className="mt-2 text-sm text-slate-500">Evaluating investigation quality…</p>
      </section>
    );
  }

  if (error) {
    return (
      <section className="rounded-lg border border-amber-200 bg-amber-50 p-4">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-amber-800">
          Investigation Quality
        </h2>
        <p className="mt-1 text-sm text-amber-900">{error}</p>
      </section>
    );
  }

  if (!evaluation) {
    return null;
  }

  const { metrics, results } = evaluation;
  const issues = results.flatMap((r) => r.detected_issues);

  return (
    <section className="rounded-lg border border-surface-border bg-white p-4">
      <div className="flex items-center justify-between gap-2 mb-3">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-slate-500">
          Investigation Quality Panel
        </h2>
        <span
          className={`text-sm font-semibold tabular-nums rounded px-2 py-0.5 border ${scoreColor(metrics.overall_score)}`}
        >
          Overall {Math.round(metrics.overall_score * 100)}%
        </span>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <ScoreCard label="Workflow" score={metrics.workflow_quality} />
        <ScoreCard label="Report" score={metrics.report_quality} />
        <ScoreCard label="Findings" score={metrics.finding_confidence} />
        <ScoreCard label="Patterns" score={metrics.pattern_confidence} />
      </div>

      {issues.length > 0 && (
        <div className="mt-3">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-slate-500 mb-1">
            Detected issues ({issues.length})
          </p>
          <ul className="text-xs text-slate-700 space-y-0.5 max-h-24 overflow-y-auto">
            {issues.slice(0, 8).map((issue) => (
              <li key={issue} className="font-mono truncate" title={issue}>
                · {issue}
              </li>
            ))}
            {issues.length > 8 && (
              <li className="text-slate-500">+{issues.length - 8} more</li>
            )}
          </ul>
        </div>
      )}
    </section>
  );
}
