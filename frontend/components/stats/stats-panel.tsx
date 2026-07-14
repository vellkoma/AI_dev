"use client";

import { useCallback, useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatCards } from "./stat-cards";
import { UsageChart } from "./usage-chart";
import { TimelineGraph } from "./timeline-graph";
import { api } from "@/lib/api";
import { Stats } from "@/types";

interface ModelUsageData {
  model_name: string;
  request_count: number;
  token_count: number;
}

interface TimelineData {
  period: string;
  request_count: number;
  token_count: number;
}

interface StatsPanelProps {
  /** チャット完了後にインクリメントすることで統計を再取得するトリガー */
  refreshTrigger?: number;
}

/** 統計パネル全体を統合するコンポーネント */
export function StatsPanel({ refreshTrigger = 0 }: StatsPanelProps) {
  const [stats, setStats] = useState<Stats>({
    total_requests: 0,
    total_tokens: 0,
    average_response_time: 0,
    estimated_cost: 0,
  });
  const [modelData, setModelData] = useState<ModelUsageData[]>([]);
  const [timelineData, setTimelineData] = useState<TimelineData[]>([]);
  const [currentPeriod, setCurrentPeriod] = useState<"daily" | "weekly">("daily");
  const [loading, setLoading] = useState(true);

  /** 全統計データを取得する */
  const fetchStats = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, modelRes, timelineRes] = await Promise.all([
        api.stats.get(),
        api.stats.byModel(),
        api.stats.timeline(currentPeriod),
      ]);
      setStats(statsRes);
      setModelData(Array.isArray(modelRes) ? modelRes : []);
      setTimelineData(Array.isArray(timelineRes) ? timelineRes : []);
    } catch (error) {
      console.error("統計データの取得に失敗しました:", error);
    } finally {
      setLoading(false);
    }
  }, [currentPeriod]);

  // 初回マウント時およびrefreshTrigger変更時にデータを再取得
  useEffect(() => {
    fetchStats();
  }, [fetchStats, refreshTrigger]);

  /** 期間変更時にタイムラインデータを再取得する */
  const handlePeriodChange = async (period: "daily" | "weekly") => {
    setCurrentPeriod(period);
    try {
      const timelineRes = await api.stats.timeline(period);
      setTimelineData(Array.isArray(timelineRes) ? timelineRes : []);
    } catch (error) {
      console.error("タイムラインデータの取得に失敗しました:", error);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        {/* ローディングスケルトン */}
        <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Card key={i}>
              <CardHeader className="pb-2">
                <div className="h-4 w-24 animate-pulse rounded bg-muted" />
              </CardHeader>
              <CardContent>
                <div className="h-8 w-20 animate-pulse rounded bg-muted" />
              </CardContent>
            </Card>
          ))}
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <Card>
            <CardContent className="pt-6">
              <div className="h-[250px] animate-pulse rounded bg-muted" />
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="h-[200px] animate-pulse rounded bg-muted" />
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* 累積統計カード */}
      <StatCards stats={stats} />

      {/* モデル使用比率チャート + タイムライングラフ */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">モデル使用比率</CardTitle>
          </CardHeader>
          <CardContent>
            <UsageChart data={modelData} />
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base">使用量推移</CardTitle>
          </CardHeader>
          <CardContent>
            <TimelineGraph
              data={timelineData}
              onPeriodChange={handlePeriodChange}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
