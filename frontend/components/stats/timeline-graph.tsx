"use client";

import { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface TimelineData {
  period: string;
  request_count: number;
  token_count: number;
}

interface TimelineGraphProps {
  data: TimelineData[];
  onPeriodChange: (period: "daily" | "weekly") => void;
}

/** 日別/週別の使用量推移を折れ線グラフで表示するコンポーネント */
export function TimelineGraph({ data, onPeriodChange }: TimelineGraphProps) {
  const [period, setPeriod] = useState<"daily" | "weekly">("daily");

  const handlePeriodChange = (newPeriod: "daily" | "weekly") => {
    setPeriod(newPeriod);
    onPeriodChange(newPeriod);
  };

  return (
    <div className="space-y-3">
      {/* 期間セレクター */}
      <div className="flex gap-2">
        <button
          onClick={() => handlePeriodChange("daily")}
          className={`rounded px-3 py-1 text-sm ${
            period === "daily"
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-muted-foreground hover:bg-muted/80"
          }`}
        >
          日別
        </button>
        <button
          onClick={() => handlePeriodChange("weekly")}
          className={`rounded px-3 py-1 text-sm ${
            period === "weekly"
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-muted-foreground hover:bg-muted/80"
          }`}
        >
          週別
        </button>
      </div>

      {/* グラフ */}
      {!data || data.length === 0 ? (
        <div className="flex h-[200px] items-center justify-center text-muted-foreground">
          データがありません
        </div>
      ) : (
        <div className="h-[200px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="period" fontSize={12} />
              <YAxis fontSize={12} />
              <Tooltip />
              <Legend />
              <Line
                type="monotone"
                dataKey="token_count"
                stroke="#8884d8"
                name="トークン数"
                strokeWidth={2}
                dot={false}
              />
              <Line
                type="monotone"
                dataKey="request_count"
                stroke="#82ca9d"
                name="リクエスト数"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}
