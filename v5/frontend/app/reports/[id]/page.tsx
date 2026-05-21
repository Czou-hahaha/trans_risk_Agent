"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getReport, type Report } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Download, ArrowLeft } from "lucide-react";
import { cn } from "@/lib/utils";

const SECTIONS = [
  { id: "business-summary", label: "Business Summary" },
  { id: "risk-hypothesis", label: "Risk Hypothesis" },
  { id: "recommended-actions", label: "Recommended Actions" },
  { id: "contributor-ranking", label: "Contributor Ranking" },
  { id: "full-report", label: "Full Report" },
] as const;

export default function ReportPage() {
  const params = useParams();
  const id = params.id as string;
  const [report, setReport] = useState<Report | null>(null);
  const [activeSection, setActiveSection] = useState<string>(SECTIONS[0].id);

  useEffect(() => {
    getReport(id).then(setReport).catch(console.error);
  }, [id]);

  function exportMarkdown() {
    if (!report) return;
    const blob = new Blob([report.markdown_export], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `investigation-report-${report.metric_name}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  if (!report) {
    return (
      <div className="p-8 text-slate-500" data-testid="page-report-loading">
        Loading report…
      </div>
    );
  }

  return (
    <div className="p-8 max-w-5xl" data-testid="page-report">
      <div className="flex items-center justify-between">
        <div>
          <Link
            href={`/investigation/${report.investigation_id}`}
            className="inline-flex items-center text-sm text-slate-500 hover:text-slate-900"
          >
            <ArrowLeft className="mr-1 h-4 w-4" />
            Back to investigation
          </Link>
          <h1 className="mt-2 text-2xl font-semibold text-slate-900">
            Investigation Report
          </h1>
          <p className="text-sm text-slate-500 mt-1">{report.goal}</p>
        </div>
        <Button
          variant="secondary"
          onClick={exportMarkdown}
          data-testid="report-export"
        >
          <Download className="mr-2 h-4 w-4" />
          Export Markdown
        </Button>
      </div>

      <nav
        className="mt-6 flex flex-wrap gap-2"
        data-testid="report-section-nav"
        aria-label="Report sections"
      >
        {SECTIONS.map((s) => (
          <button
            key={s.id}
            type="button"
            onClick={() => {
              setActiveSection(s.id);
              document.getElementById(s.id)?.scrollIntoView({ behavior: "smooth" });
            }}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-medium transition-colors",
              activeSection === s.id
                ? "bg-blue-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            )}
          >
            {s.label}
          </button>
        ))}
      </nav>

      <div className="mt-6 space-y-6">
        <Card id="business-summary" data-testid="report-section-business-summary">
          <CardHeader>
            <CardTitle>Business Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed text-slate-700">
              {report.business_summary}
            </p>
          </CardContent>
        </Card>

        <Card id="risk-hypothesis" data-testid="report-section-risk-hypothesis">
          <CardHeader>
            <CardTitle>Risk Hypothesis</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed text-slate-700">
              {report.risk_hypothesis}
            </p>
          </CardContent>
        </Card>

        <Card id="recommended-actions" data-testid="report-section-recommended-actions">
          <CardHeader>
            <CardTitle>Recommended Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">
              {report.recommended_actions.map((a, i) => (
                <li key={i}>{a}</li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card id="contributor-ranking" data-testid="report-section-contributor-ranking">
          <CardHeader>
            <CardTitle>Contributor Ranking</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto rounded-lg border" data-testid="report-table">
              <table className="w-full text-sm">
                <thead className="bg-surface-muted text-left text-xs uppercase text-slate-500">
                  <tr>
                    <th className="px-3 py-2">Rank</th>
                    <th className="px-3 py-2">Dimension</th>
                    <th className="px-3 py-2">Value</th>
                    <th className="px-3 py-2">Contribution</th>
                    <th className="px-3 py-2">Delta</th>
                  </tr>
                </thead>
                <tbody>
                  {report.contributor_ranking.map((r) => (
                    <tr key={r.rank} className="border-t">
                      <td className="px-3 py-2">{r.rank}</td>
                      <td className="px-3 py-2">{r.dimension_name}</td>
                      <td className="px-3 py-2 font-medium">{r.dimension_value}</td>
                      <td className="px-3 py-2 font-mono text-xs">
                        {r.contribution_pp >= 0 ? "+" : ""}
                        {r.contribution_pp.toFixed(2)}pp
                      </td>
                      <td className="px-3 py-2 font-mono text-xs">
                        {r.delta_pp >= 0 ? "+" : ""}
                        {r.delta_pp.toFixed(2)}pp
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card id="full-report" data-testid="report-section-full-report">
          <CardHeader>
            <CardTitle>Full Report (Markdown)</CardTitle>
          </CardHeader>
          <CardContent>
            <div
              className="prose prose-sm max-w-none text-slate-800"
              data-testid="report-markdown"
            >
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {report.markdown_export}
              </ReactMarkdown>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
