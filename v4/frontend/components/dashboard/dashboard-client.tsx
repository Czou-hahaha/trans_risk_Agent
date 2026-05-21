"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { getDashboard, type DashboardData } from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { AlertTriangle, ArrowRight, FileBarChart, Loader2, RefreshCw } from "lucide-react";

export function DashboardClient() {
  const pathname = usePathname();
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getDashboard());
    } catch (e) {
      setData(null);
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, pathname]);

  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === "visible") load();
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => document.removeEventListener("visibilitychange", onVisible);
  }, [load]);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center gap-2 p-16 text-slate-500">
        <Loader2 className="h-5 w-5 animate-spin" />
        加载工作台数据…
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-semibold">Dashboard</h1>
        <p className="mt-4 text-slate-600">无法加载数据：{error}</p>
        <p className="mt-2 text-sm text-slate-500">
          请确认后端已启动：
          <code className="mx-1 rounded bg-slate-100 px-1">./scripts/start-backend.sh</code>
          （端口 8001）
        </p>
        <Button className="mt-4" variant="secondary" onClick={load}>
          <RefreshCw className="mr-2 h-4 w-4" />
          重试
        </Button>
      </div>
    );
  }

  if (!data) return null;

  const { kpis, latest_investigations, latest_risk_alerts, latest_reports } = data;

  return (
    <div className="p-8 space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Dashboard</h1>
          <p className="mt-1 text-sm text-slate-500">
            调查任务总览 · 共 {kpis.total_investigations} 次调查
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="ghost" size="sm" onClick={load} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
          </Button>
          <Link href="/investigation/new">
            <Button>发起新调查</Button>
          </Link>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="调查总数" value={kpis.total_investigations} />
        <KpiCard label="进行中" value={kpis.running_investigations} accent="amber" />
        <KpiCard label="已完成" value={kpis.completed_investigations} accent="emerald" />
        <KpiCard label="失败" value={kpis.failed_investigations} accent="red" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>最近调查</CardTitle>
            <FileBarChart className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent className="space-y-3">
            {latest_investigations.length === 0 && (
              <p className="text-sm text-slate-500">
                还没有调查记录，点击「发起新调查」开始。
              </p>
            )}
            {latest_investigations.map((inv) => (
              <Link
                key={inv.id}
                href={`/investigation/${inv.id}`}
                className="flex items-center justify-between rounded-lg border border-surface-border p-3 hover:bg-surface-muted transition-colors"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-900">
                    {inv.goal}
                  </p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {inv.metric_name.toUpperCase()} ·{" "}
                    {new Date(inv.created_at).toLocaleString("zh-CN")}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-3">
                  <StatusBadge status={inv.status} />
                  <ArrowRight className="h-4 w-4 text-slate-400" />
                </div>
              </Link>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle>风险告警（来自 Monitor）</CardTitle>
            <AlertTriangle className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent className="space-y-3">
            {latest_risk_alerts.length === 0 && (
              <p className="text-sm text-slate-500">
                暂无告警。完成一次需调查的分析后，Monitor 异常会显示在这里。
              </p>
            )}
            {latest_risk_alerts.map((a) => (
              <Link
                key={a.id}
                href={`/investigation/${a.id}`}
                className="block rounded-lg border border-amber-100 bg-amber-50/50 p-3 hover:bg-amber-50"
              >
                <p className="text-sm font-medium text-slate-900">
                  {a.metric_name.toUpperCase()} — {a.severity}
                </p>
                <p className="mt-1 text-xs text-slate-600">{a.summary}</p>
              </Link>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>最近报告</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {latest_reports.length === 0 && (
            <p className="text-sm text-slate-500">
              暂无报告。调查跑完 Summary 阶段后会自动生成。
            </p>
          )}
          {latest_reports.map((inv) =>
            inv.report_id ? (
              <Link
                key={inv.id}
                href={`/reports/${inv.report_id}`}
                className="flex items-center justify-between rounded-lg border p-3 hover:bg-surface-muted"
              >
                <span className="text-sm font-medium">{inv.goal}</span>
                <ArrowRight className="h-4 w-4 text-slate-400" />
              </Link>
            ) : null
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function KpiCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: number;
  accent?: "amber" | "emerald" | "red";
}) {
  const ring =
    accent === "amber"
      ? "border-amber-200"
      : accent === "emerald"
        ? "border-emerald-200"
        : accent === "red"
          ? "border-red-200"
          : "border-surface-border";
  return (
    <Card className={ring}>
      <CardContent className="pt-5">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
          {label}
        </p>
        <p className="mt-2 text-3xl font-semibold text-slate-900">{value}</p>
      </CardContent>
    </Card>
  );
}
