"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import {
  getExecutiveIntelligence,
  type ExecutiveIntelligence,
  type IntelligenceItem,
} from "@/lib/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Brain,
  GitBranch,
  Layers,
  Loader2,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  TrendingDown,
  TrendingUp,
} from "lucide-react";

export function ExecutiveDashboardClient() {
  const [data, setData] = useState<ExecutiveIntelligence | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await getExecutiveIntelligence());
    } catch (e) {
      setData(null);
      setError(e instanceof Error ? e.message : "加载失败");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  if (loading && !data) {
    return (
      <div className="flex items-center justify-center gap-2 p-16 text-slate-500">
        <Loader2 className="h-5 w-5 animate-spin" />
        加载 Executive Intelligence…
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="p-8">
        <h1 className="text-2xl font-semibold">Executive Intelligence</h1>
        <p className="mt-4 text-slate-600">无法加载：{error}</p>
        <Button className="mt-4" variant="secondary" onClick={load}>
          <RefreshCw className="mr-2 h-4 w-4" />
          重试
        </Button>
      </div>
    );
  }

  if (!data) return null;

  const {
    weekly_summary,
    top_recurring_contributors,
    most_unstable_segments,
    highest_risk_strategies,
    recurring_deterioration_patterns,
    trend_intelligence,
    pattern_intelligence,
    message,
    data_available,
  } = data;

  return (
    <div
      className="min-h-full bg-gradient-to-b from-slate-50 via-[var(--background)] to-slate-100"
      data-testid="page-executive"
    >
      <div className="border-b border-surface-border bg-white/80 backdrop-blur-sm">
        <div className="mx-auto max-w-7xl px-8 py-6">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-blue-600">
                <Sparkles className="h-3.5 w-3.5" />
                Risk Intelligence Platform
              </div>
              <h1 className="mt-1 text-2xl font-semibold text-slate-900">
                Executive Intelligence Dashboard
              </h1>
              <p className="mt-1 max-w-2xl text-sm text-slate-500">
                高层风控 intelligence overview — 跨调查模式、趋势信号与周报摘要
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm" onClick={load} disabled={loading}>
                <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              </Button>
              <Link href="/investigation">
                <Button variant="secondary" size="sm">
                  Investigation Workspace
                </Button>
              </Link>
            </div>
          </div>
          {!data_available && message && (
            <p className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
              {message}
            </p>
          )}
        </div>
      </div>

      <div className="mx-auto max-w-7xl space-y-8 px-8 py-8">
        <WeeklySummaryCard summary={weekly_summary} />

        <section data-testid="executive-risk-overview">
          <SectionHeading
            icon={Layers}
            title="Risk Intelligence Overview"
            subtitle="跨调查聚合的高优先级信号"
          />
          <div className="mt-4 grid gap-4 lg:grid-cols-2">
            <IntelligenceListCard
              title="Top Recurring Contributors"
              subtitle="反复出现在 Top 贡献中的维度"
              icon={BarChart3}
              items={top_recurring_contributors}
              emptyHint="完成多次 dimension_contribution 调查后将出现"
              testId="executive-recurring-contributors"
            />
            <IntelligenceListCard
              title="Most Unstable Segments"
              subtitle="segment 稳定性反复恶化"
              icon={TrendingDown}
              items={most_unstable_segments}
              accent="amber"
              emptyHint="segment_stability findings 不足"
            />
            <IntelligenceListCard
              title="Highest-risk Strategies"
              subtitle="策略副作用、审批风险与体量权衡"
              icon={ShieldAlert}
              items={highest_risk_strategies}
              accent="red"
              emptyHint="strategy_impact findings 不足"
            />
            <IntelligenceListCard
              title="Recurring Deterioration Patterns"
              subtitle="历史反复恶化模式"
              icon={AlertTriangle}
              items={recurring_deterioration_patterns}
              accent="red"
              emptyHint="暂无恶化复发模式"
            />
          </div>
        </section>

        <section>
          <SectionHeading
            icon={Activity}
            title="Trend Intelligence"
            subtitle="risk · approval · volume-risk tradeoff"
          />
          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <IntelligenceListCard
              title="Risk Trend Shifts"
              subtitle="风险指标趋势偏移"
              icon={TrendingUp}
              items={trend_intelligence.risk_trend_shifts}
              compact
              emptyHint="暂无风险趋势信号"
            />
            <IntelligenceListCard
              title="Approval Trend Shifts"
              subtitle="通过率与风险联动"
              icon={GitBranch}
              items={trend_intelligence.approval_trend_shifts}
              compact
              emptyHint="暂无审批趋势信号"
            />
            <IntelligenceListCard
              title="Volume–Risk Tradeoff"
              subtitle="体量损失 vs 风险改善"
              icon={BarChart3}
              items={trend_intelligence.volume_risk_tradeoffs}
              compact
              emptyHint="暂无体量-风险权衡信号"
            />
          </div>
        </section>

        <section data-testid="executive-pattern-intelligence">
          <SectionHeading
            icon={Brain}
            title="Pattern Intelligence"
            subtitle="recurring · historical · cross-investigation"
          />
          <div className="mt-4 grid gap-4 lg:grid-cols-3">
            <IntelligenceListCard
              title="Recurring Patterns"
              subtitle="当前窗口内检测到的模式"
              icon={Sparkles}
              items={pattern_intelligence.recurring_patterns}
              compact
              emptyHint="暂无复发模式"
            />
            <IntelligenceListCard
              title="Historical Recurrence"
              subtitle="按出现频次排序"
              icon={Layers}
              items={pattern_intelligence.historical_recurrence}
              compact
              emptyHint="历史复发数据不足"
              testId="executive-historical-intelligence"
            />
            <IntelligenceListCard
              title="Cross-investigation Signals"
              subtitle="跨调查高置信信号"
              icon={GitBranch}
              items={pattern_intelligence.cross_investigation_signals}
              compact
              emptyHint="跨调查信号不足"
            />
          </div>
        </section>
      </div>
    </div>
  );
}

function SectionHeading({
  icon: Icon,
  title,
  subtitle,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  subtitle: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-blue-50 text-blue-600">
        <Icon className="h-4 w-4" />
      </div>
      <div>
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        <p className="text-xs text-slate-500">{subtitle}</p>
      </div>
    </div>
  );
}

function WeeklySummaryCard({
  summary,
}: {
  summary: ExecutiveIntelligence["weekly_summary"];
}) {
  return (
    <Card className="overflow-hidden border-blue-100 shadow-md">
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-blue-900 px-6 py-5 text-white">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <p className="text-xs font-medium uppercase tracking-wider text-blue-200">
              Weekly Risk Intelligence Summary
            </p>
            <h2 className="mt-1 text-lg font-semibold">{summary.period_label}</h2>
          </div>
          <div className="flex gap-4 text-xs text-slate-300">
            <span>{summary.investigation_count} 次调查</span>
            <span>{summary.pattern_count} 条模式</span>
          </div>
        </div>
        <p className="mt-4 text-sm leading-relaxed text-slate-100">{summary.headline}</p>
      </div>
      <CardContent className="pt-5">
        {summary.highlights.length === 0 ? (
          <p className="text-sm text-slate-500">
            本周暂无高亮项。系统将在过去 7 天内积累足够 findings 后自动生成摘要。
          </p>
        ) : (
          <ul className="space-y-3">
            {summary.highlights.map((h, i) => (
              <li
                key={`${h.category}-${i}`}
                className="flex gap-3 rounded-lg border border-surface-border bg-surface-muted/50 p-3"
              >
                <SeverityDot severity={h.severity} />
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
                      {h.category}
                    </span>
                  </div>
                  <p className="mt-0.5 text-sm font-medium text-slate-900">{h.headline}</p>
                  <p className="mt-1 text-xs text-slate-500">{h.detail}</p>
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  );
}

function SeverityDot({ severity }: { severity: string }) {
  const color =
    severity === "high"
      ? "bg-red-500"
      : severity === "low"
        ? "bg-emerald-500"
        : "bg-amber-500";
  return (
    <span
      className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${color}`}
      aria-hidden
    />
  );
}

function IntelligenceListCard({
  title,
  subtitle,
  icon: Icon,
  items,
  emptyHint,
  accent,
  compact,
  testId,
}: {
  title: string;
  subtitle: string;
  icon: React.ComponentType<{ className?: string }>;
  items: IntelligenceItem[];
  emptyHint: string;
  accent?: "amber" | "red";
  compact?: boolean;
  testId?: string;
}) {
  const border =
    accent === "red"
      ? "border-red-100"
      : accent === "amber"
        ? "border-amber-100"
        : "border-surface-border";

  return (
    <Card className={border} data-testid={testId}>
      <CardHeader className="flex flex-row items-start justify-between gap-2 pb-2">
        <div>
          <CardTitle>{title}</CardTitle>
          <p className="mt-0.5 text-xs text-slate-500">{subtitle}</p>
        </div>
        <Icon
          className={`h-4 w-4 shrink-0 ${
            accent === "red"
              ? "text-red-400"
              : accent === "amber"
                ? "text-amber-500"
                : "text-slate-400"
          }`}
        />
      </CardHeader>
      <CardContent className={compact ? "space-y-2" : "space-y-3"}>
        {items.length === 0 ? (
          <p className="text-sm text-slate-500">{emptyHint}</p>
        ) : (
          items.map((item) => <IntelligenceRow key={item.id} item={item} compact={compact} />)
        )}
      </CardContent>
    </Card>
  );
}

function IntelligenceRow({
  item,
  compact,
}: {
  item: IntelligenceItem;
  compact?: boolean;
}) {
  const invId = item.investigation_ids[0];
  const content = (
    <div
      className={`rounded-lg border border-surface-border transition-colors hover:bg-surface-muted ${
        compact ? "p-2.5" : "p-3"
      } ${invId ? "cursor-pointer" : ""}`}
    >
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-slate-900 truncate">{item.title}</p>
        <ConfidenceBadge score={item.confidence_score} />
      </div>
      <p className={`mt-1 text-slate-600 ${compact ? "text-xs line-clamp-2" : "text-xs"}`}>
        {item.summary}
      </p>
      <div className="mt-2 flex flex-wrap gap-2 text-[10px] text-slate-500">
        {item.metric_name && (
          <span className="rounded bg-slate-100 px-1.5 py-0.5 uppercase">
            {item.metric_name}
          </span>
        )}
        {item.occurrence_count > 0 && (
          <span>×{item.occurrence_count}</span>
        )}
        {item.investigation_ids.length > 0 && (
          <span>{item.investigation_ids.length} investigations</span>
        )}
      </div>
    </div>
  );

  if (invId) {
    return <Link href={`/investigation/${invId}`}>{content}</Link>;
  }
  return content;
}

function ConfidenceBadge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const tone =
    pct >= 70 ? "text-emerald-700 bg-emerald-50" : pct >= 40 ? "text-amber-700 bg-amber-50" : "text-slate-600 bg-slate-100";
  return (
    <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${tone}`}>
      {pct}%
    </span>
  );
}
