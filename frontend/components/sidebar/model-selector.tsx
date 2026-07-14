"use client";

import { useEffect, useState } from "react";
import { Bot } from "lucide-react";
import { Select, SelectOption } from "@/components/ui/select";
import { useToast } from "@/components/ui/use-toast";
import { api } from "@/lib/api";
import type { ModelInfo } from "@/types";

interface ModelSelectorProps {
  /** 現在選択中のモデル名 */
  currentModel: string;
  /** モデル変更時のコールバック */
  onModelChange: (model: string) => void;
}

export function ModelSelector({
  currentModel,
  onModelChange,
}: ModelSelectorProps) {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  // モデル一覧を取得
  useEffect(() => {
    api.models
      .list()
      .then((data: { models: ModelInfo[] }) => {
        setModels(data.models ?? []);
      })
      .catch(() => {
        // ネットワークエラー時は空のまま
        setModels([]);
      });
  }, []);

  // モデル切り替えハンドラー
  const handleModelChange = async (value: string) => {
    if (value === currentModel || !value) return;

    setLoading(true);
    const selectedModel = models.find((m) => m.name === value);
    const provider = selectedModel?.provider ?? "";

    try {
      const result = await api.models.switch(value, provider);
      if (result.success) {
        onModelChange(value);
        toast({
          title: "モデル切り替え完了",
          description: `${value} に切り替えました`,
        });
      } else {
        toast({
          title: "モデル切り替え失敗",
          description: result.message || "切り替えに失敗しました",
          variant: "destructive",
        });
      }
    } catch {
      toast({
        title: "モデル切り替えエラー",
        description: "サーバーとの通信に失敗しました",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-2">
      <label className="flex items-center gap-2 text-sm font-medium">
        <Bot className="h-4 w-4" />
        モデル選択
      </label>
      <Select
        value={currentModel}
        onValueChange={handleModelChange}
        disabled={loading}
        aria-label="LLMモデルを選択"
      >
        {models.length === 0 ? (
          <SelectOption value="" disabled>
            モデルを読み込み中...
          </SelectOption>
        ) : (
          models.map((model) => (
            <SelectOption
              key={model.name}
              value={model.name}
              disabled={model.status === "unavailable"}
            >
              {model.name} ({model.provider})
              {model.status === "unavailable" ? " - 利用不可" : ""}
            </SelectOption>
          ))
        )}
      </Select>
    </div>
  );
}
