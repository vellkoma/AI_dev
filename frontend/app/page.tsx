"use client";

import { useState, useCallback } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { Sidebar } from "@/components/sidebar/sidebar";
import { HistoryPanel } from "@/components/history/history-panel";
import { ChatPanel } from "@/components/chat/chat-panel";
import { StatsPanel } from "@/components/stats/stats-panel";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import type { Message } from "@/types";

export default function Home() {
  // --- 状態管理 ---
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [currentModel, setCurrentModel] = useState("gpt-3.5-turbo");
  const [ragEnabled, setRagEnabled] = useState(false);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [statsOpen, setStatsOpen] = useState(false);

  // --- セッション選択時：メッセージ読み込み ---
  const handleSelectSession = useCallback(async (sessionId: string) => {
    setCurrentSessionId(sessionId);
    try {
      const sessionData = await api.history.get(sessionId);
      // セッション詳細からメッセージを取得
      const loadedMessages: Message[] = Array.isArray(sessionData.messages)
        ? sessionData.messages
        : [];
      setMessages(loadedMessages);
    } catch (error) {
      console.error("セッションの読み込みに失敗しました:", error);
      setMessages([]);
    }
  }, []);

  // --- 新規セッション作成 ---
  const handleNewSession = useCallback(
    (sessionId: string) => {
      setCurrentSessionId(sessionId);
      setMessages([]);
    },
    []
  );

  // --- メッセージ更新（チャット完了検出付き） ---
  const handleMessagesChange = useCallback(
    (updatedMessages: Message[]) => {
      // アシスタントの最新メッセージが追加された場合（チャット完了）を検出
      const prevLength = messages.length;
      const newLength = updatedMessages.length;
      if (
        newLength > prevLength &&
        updatedMessages[newLength - 1]?.role === "assistant"
      ) {
        // チャット完了 → 統計を更新
        setRefreshTrigger((prev) => prev + 1);
      }
      setMessages(updatedMessages);
    },
    [messages.length]
  );

  // --- サイドバーコンテンツ（設定 + 履歴パネル） ---
  const sidebarContent = (
    <div className="flex flex-col h-full gap-0">
      {/* 設定パネル（モデル選択・RAG切り替え） */}
      <div className="shrink-0">
        <Sidebar
          currentModel={currentModel}
          onModelChange={setCurrentModel}
          ragEnabled={ragEnabled}
          onRagToggle={setRagEnabled}
        />
      </div>

      {/* 履歴パネル */}
      <div className="flex-1 min-h-0 border-t">
        <HistoryPanel
          currentSessionId={currentSessionId ?? undefined}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
        />
      </div>
    </div>
  );

  return (
    <DashboardLayout sidebar={sidebarContent}>
      <div className="flex flex-col h-full">
        {/* メインチャットエリア */}
        <div className="flex-1 min-h-0">
          <ChatPanel
            messages={messages}
            onMessagesChange={handleMessagesChange}
            ragEnabled={ragEnabled}
            sessionId={currentSessionId ?? undefined}
          />
        </div>

        {/* 統計パネル（折りたたみ可能） */}
        <div className="border-t">
          <Button
            variant="ghost"
            size="sm"
            className="w-full flex items-center justify-center gap-1 py-1 h-8 rounded-none"
            onClick={() => setStatsOpen(!statsOpen)}
            aria-expanded={statsOpen}
            aria-controls="stats-panel"
          >
            {statsOpen ? (
              <ChevronDown className="h-4 w-4" />
            ) : (
              <ChevronUp className="h-4 w-4" />
            )}
            <span className="text-xs text-muted-foreground">
              {statsOpen ? "統計を閉じる" : "統計を表示"}
            </span>
          </Button>

          {statsOpen && (
            <div
              id="stats-panel"
              className="max-h-[40vh] overflow-y-auto p-4 bg-muted/30"
            >
              <StatsPanel refreshTrigger={refreshTrigger} />
            </div>
          )}
        </div>
      </div>
    </DashboardLayout>
  );
}
