"use client";

import { Database } from "lucide-react";
import { Toggle } from "@/components/ui/toggle";
import { cn } from "@/lib/utils";

interface RagToggleProps {
  /** RAGモードが有効かどうか */
  enabled: boolean;
  /** RAGモード切り替え時のコールバック */
  onToggle: (enabled: boolean) => void;
}

export function RagToggle({ enabled, onToggle }: RagToggleProps) {
  return (
    <div className="space-y-2">
      <label className="flex items-center gap-2 text-sm font-medium">
        <Database className="h-4 w-4" />
        RAGモード
      </label>
      <Toggle
        pressed={enabled}
        onPressedChange={onToggle}
        variant="outline"
        className={cn(
          "w-full justify-start gap-2",
          enabled && "border-primary bg-primary/10 text-primary"
        )}
        aria-label="RAGモードの切り替え"
      >
        <span
          className={cn(
            "inline-block h-3 w-3 rounded-full",
            enabled ? "bg-green-500" : "bg-muted-foreground/40"
          )}
        />
        {enabled ? "ON — ドキュメント検索有効" : "OFF"}
      </Toggle>
    </div>
  );
}
