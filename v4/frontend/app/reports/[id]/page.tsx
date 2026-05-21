"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { getReport, type Report } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Download, ArrowLeft } from "lucide-react";

export default function ReportPage() {
  const params = useParams();
  const id = params.id as string;
  const [report, setReport] = useState<Report | null>(null);

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
    return <div className="p-8 text-slate-500">Loading report…</div>;
  }

  return (
    <div className="p-8 max-w-4xl space-y-6">
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
        <Button variant="secondary" onClick={exportMarkdown}>
          <Download className="mr-2 h-4 w-4" />
          Export Markdown
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Business Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed text-slate-700">
            {report.business_summary}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Risk Hypothesis</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed text-slate-700">
            {report.risk_hypothesis}
          </p>
        </CardContent>
      </Card>

      <Card>
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

      <Card>
        <CardHeader>
          <CardTitle>Contributor Ranking</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto rounded-lg border">
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
    </div>
  );
}
