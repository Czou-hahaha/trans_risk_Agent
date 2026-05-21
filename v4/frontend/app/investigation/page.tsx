"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { listInvestigations, runInvestigation, type Investigation } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { Loader2 } from "lucide-react";

export default function InvestigationWorkspacePage() {
  const router = useRouter();
  const [metric, setMetric] = useState("fpd7");
  const [analysisDate, setAnalysisDate] = useState("2026-05-20");
  const [loading, setLoading] = useState(false);
  const [recent, setRecent] = useState<Investigation[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listInvestigations(10)
      .then(setRecent)
      .catch(() => setRecent([]));
  }, []);

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      const inv = await runInvestigation({
        metric_name: metric.trim(),
        analysis_date: analysisDate,
      });
      router.push(`/investigation/${inv.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start");
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-4xl">
      <h1 className="text-2xl font-semibold text-slate-900">
        Risk Investigation Workspace
      </h1>
      <p className="mt-1 text-sm text-slate-500">
        Deterministic orchestration across monitor, trend, contribution, stability,
        strategy impact, and report synthesis.
      </p>

      <Card className="mt-8">
        <CardHeader>
          <CardTitle>Start Investigation</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block text-sm">
              <span className="text-slate-600">Metric</span>
              <input
                className="mt-1 w-full rounded-lg border border-surface-border px-3 py-2 text-sm"
                value={metric}
                onChange={(e) => setMetric(e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="text-slate-600">Analysis date</span>
              <input
                type="date"
                className="mt-1 w-full rounded-lg border border-surface-border px-3 py-2 text-sm"
                value={analysisDate}
                onChange={(e) => setAnalysisDate(e.target.value)}
              />
            </label>
          </div>
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button onClick={handleRun} disabled={loading} size="lg">
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Running workflow…
              </>
            ) : (
              "Run Investigation"
            )}
          </Button>
        </CardContent>
      </Card>

      {recent.length > 0 && (
        <Card className="mt-8">
          <CardHeader>
            <CardTitle className="text-base">Recent Investigations</CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-slate-100">
            {recent.map((inv) => (
              <Link
                key={inv.id}
                href={`/investigation/${inv.id}`}
                className="flex items-center justify-between py-3 hover:bg-slate-50 -mx-2 px-2 rounded-lg"
              >
                <div>
                  <p className="text-sm font-medium text-slate-900">{inv.goal}</p>
                  <p className="text-xs text-slate-500">
                    {inv.metric_name.toUpperCase()} · {new Date(inv.created_at).toLocaleString()}
                  </p>
                </div>
                <StatusBadge status={inv.status} />
              </Link>
            ))}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
