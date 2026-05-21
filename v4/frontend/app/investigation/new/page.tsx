"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { createInvestigation } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Loader2 } from "lucide-react";

const DEFAULT_GOAL = "分析本周FPD7上升原因";

export default function NewInvestigationPage() {
  const router = useRouter();
  const [goal, setGoal] = useState(DEFAULT_GOAL);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleRun() {
    setLoading(true);
    setError(null);
    try {
      const inv = await createInvestigation(goal.trim());
      router.push(`/investigation/${inv.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to start investigation");
      setLoading(false);
    }
  }

  return (
    <div className="p-8 max-w-2xl">
      <h1 className="text-2xl font-semibold text-slate-900">New Investigation</h1>
      <p className="mt-1 text-sm text-slate-500">
        Describe what you want to investigate. The deterministic workflow will run
        monitor → contribution → summary.
      </p>

      <Card className="mt-8">
        <CardHeader>
          <CardTitle>Investigation Goal</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <textarea
            className="w-full min-h-[120px] rounded-lg border border-surface-border bg-white px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-brand/30"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
            placeholder="分析本周FPD7上升原因"
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button onClick={handleRun} disabled={loading || !goal.trim()} size="lg">
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Running…
              </>
            ) : (
              "Run Investigation"
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
