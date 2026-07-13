"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Coins, MessageSquare, Clock, DollarSign } from "lucide-react";
import { Stats } from "@/types";

interface StatCardsProps {
  stats: Stats;
}

/** 累積統計情報を4つのカードで表示するコンポーネント */
export function StatCards({ stats }: StatCardsProps) {
  const cards = [
    {
      title: "累積トークン数",
      value: stats.total_tokens.toLocaleString(),
      unit: "tokens",
      icon: Coins,
    },
    {
      title: "リクエスト数",
      value: stats.total_requests.toLocaleString(),
      unit: "回",
      icon: MessageSquare,
    },
    {
      title: "平均応答時間",
      value: stats.average_response_time.toFixed(0),
      unit: "ms",
      icon: Clock,
    },
    {
      title: "推定コスト",
      value: `$${stats.estimated_cost.toFixed(4)}`,
      unit: "",
      icon: DollarSign,
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      {cards.map((card) => {
        const Icon = card.icon;
        return (
          <Card key={card.title}>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {card.title}
              </CardTitle>
              <Icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <p className="text-2xl font-bold">
                {card.value}
                {card.unit && (
                  <span className="ml-1 text-sm font-normal text-muted-foreground">
                    {card.unit}
                  </span>
                )}
              </p>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
