"use client";

import ReactMarkdown from "react-markdown";

export function ReportPreview({
  executiveSummary,
  markdown,
  loading,
}: {
  executiveSummary?: string | null;
  markdown?: string | null;
  loading?: boolean;
}) {
  if (loading) {
    return <p className="text-sm text-slate-500 p-4">Generating report…</p>;
  }

  return (
    <div className="prose prose-sm max-w-none p-4 text-slate-800">
      {executiveSummary && (
        <div className="mb-4 rounded-lg border border-blue-100 bg-blue-50/50 p-4 not-prose">
          <p className="text-xs font-semibold uppercase tracking-wide text-blue-700">
            Executive Summary
          </p>
          <p className="mt-2 text-sm text-slate-800 leading-relaxed">{executiveSummary}</p>
        </div>
      )}
      {markdown ? (
        <ReactMarkdown>{markdown}</ReactMarkdown>
      ) : (
        <p className="text-slate-500 text-sm">Report will appear when investigation completes.</p>
      )}
    </div>
  );
}
