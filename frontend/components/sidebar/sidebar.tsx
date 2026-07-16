"use client";

import { useState } from "react";
import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { ThemeToggle } from "@/components/theme-toggle";
import { cn } from "@/lib/utils";
import { ModelSelector } from "./model-selector";

interface SidebarProps {
  /** 現在選択中のモデル名 */
  currentModel: string;
  /** モデル変更時のコールバック */
  onModelChange: (model: string) => void;
}

export function Sidebar({
  currentModel,
  onModelChange,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "flex h-full flex-col border-r bg-background transition-all duration-200",
        collapsed ? "w-12" : "w-64"
      )}
    >
      {/* 折りたたみ/展開ボタン */}
      <div className="flex items-center justify-end p-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? "サイドバーを展開" : "サイドバーを折りたたむ"}
          className="h-8 w-8"
        >
          {collapsed ? (
            <PanelLeftOpen className="h-4 w-4" />
          ) : (
            <PanelLeftClose className="h-4 w-4" />
          )}
        </Button>
      </div>

      {/* 折りたたみ時はコンテンツを非表示 */}
      {!collapsed && (
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto px-3 pb-3">
          {/* モデル選択 */}
          <ModelSelector
            currentModel={currentModel}
            onModelChange={onModelChange}
          />

          {/* スペーサー：テーマ切り替えを下部に配置 */}
          <div className="flex-1" />

          <Separator />

          {/* テーマ切り替え */}
          <div className="flex items-center justify-between">
            <span className="text-xs text-muted-foreground">テーマ</span>
            <ThemeToggle />
          </div>
        </div>
      )}
    </aside>
  );
}
