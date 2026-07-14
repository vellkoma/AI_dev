"use client";

import { useState, useEffect, useCallback } from "react";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";
import type { SessionSummary } from "@/types";
import { SessionSearch } from "./session-search";
import { SessionList } from "./session-list";

interface HistoryPanelProps {
  currentSessionId?: string;
  onSelectSession: (sessionId: string) => void;
  onNewSession?: (sessionId: string) => void;
}

/**
 * 履歴パネル統合コンポーネント
 * セッション一覧・検索・新規作成を統合する
 */
export function HistoryPanel({
  currentSessionId,
  onSelectSession,
  onNewSession,
}: HistoryPanelProps) {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(false);

  // セッション一覧を取得
  const fetchSessions = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.history.list();
      setSessions(data);
    } catch (error) {
      console.error("セッション一覧の取得に失敗しました:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [fetchSessions]);

  // キーワード検索
  const handleSearch = useCallback(async (keyword: string) => {
    if (!keyword.trim()) {
      // キーワードが空の場合は全件取得
      setLoading(true);
      try {
        const data = await api.history.list();
        setSessions(data);
      } catch (error) {
        console.error("セッション一覧の取得に失敗しました:", error);
      } finally {
        setLoading(false);
      }
      return;
    }

    setLoading(true);
    try {
      const data = await api.history.search(keyword);
      setSessions(data);
    } catch (error) {
      console.error("検索に失敗しました:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  // 新規セッション作成
  const handleNewSession = async () => {
    try {
      const newSession = await api.history.create();
      await fetchSessions();
      if (onNewSession) {
        onNewSession(newSession.session_id);
      }
    } catch (error) {
      console.error("新規セッションの作成に失敗しました:", error);
    }
  };

  // セッション削除
  const handleDelete = async (sessionId: string) => {
    try {
      await api.history.delete(sessionId);
      await fetchSessions();
    } catch (error) {
      console.error("セッションの削除に失敗しました:", error);
    }
  };

  return (
    <div className="flex flex-col gap-3 h-full p-4">
      <Button onClick={handleNewSession} className="w-full">
        <Plus className="h-4 w-4 mr-2" />
        新しいチャット
      </Button>

      <SessionSearch onSearch={handleSearch} />

      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <p className="text-sm">読み込み中...</p>
          </div>
        ) : (
          <SessionList
            sessions={sessions}
            currentSessionId={currentSessionId}
            onSelect={onSelectSession}
            onDelete={handleDelete}
          />
        )}
      </div>
    </div>
  );
}
