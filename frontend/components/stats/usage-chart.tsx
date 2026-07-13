"use client";

import { PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer } from "recharts";

interface ModelUsageData {
  model_name: string;
  request_count: number;
  token_count: number;
}

interface UsageChartProps {
  data: ModelUsageData[];
}

// モデルごとの色パレット
const COLORS = ["#8884d8", "#82ca9d", "#ffc658", "#ff7300", "#0088fe", "#00c49f"];

/** モデルごとの使用比率を円グラフで表示するコンポーネント */
export function UsageChart({ data }: UsageChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="flex h-[250px] items-center justify-center text-muted-foreground">
        データがありません
      </div>
    );
  }

  const chartData = data.map((item) => ({
    name: item.model_name,
    value: item.request_count,
  }));

  return (
    <div className="h-[250px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={chartData}
            cx="50%"
            cy="50%"
            innerRadius={50}
            outerRadius={80}
            dataKey="value"
            label={({ name, percent }) =>
              `${name} (${(percent * 100).toFixed(0)}%)`
            }
            labelLine={false}
          >
            {chartData.map((_, index) => (
              <Cell
                key={`cell-${index}`}
                fill={COLORS[index % COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number) => [`${value} リクエスト`, "使用数"]}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
