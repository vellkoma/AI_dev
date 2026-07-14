"use client";

import { useState } from "react";
import { Trash2, MessageSquare, Clock } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import type { SessionSummary } from "@/types";

interface SessionListProps {
  sessions: SessionSummary[];
  currentSessionId?: string;
  onSelect: (sessionId: string) => void;
  onDelete: (sessionId: string) => void;
}

/**
 * 相対日付をフォーマットする（例: "2時間前", "昨日", "3日前"）
 */
function formatRelativeDate(timestamp: number): string {
  const now = Date.now();
  const date = new Date(timestamp * 1000);
  const diffMs = now - date.getTime();
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) {
    return "たった今";
  } else if (diffMinutes < 60) {
    return `${diffMinutes}分前`;
  } else if (diffHours < 24) {
    return `${diffHours}時間前`;
  } else if (diffDays === 1) {
    return "昨日";
  } else if (diffDays < 7) {
    return `${diffDays}日前`;
  } else if (diffDays < 30) {
    const weeks = Math.floor(diffDays / 7);
    return `${weeks}週間前`;
  } else {
    const month = date.getMonth() + 1;
    const day = date.getDate();
    return `${month}月${day}日`;
  }
}

/**
 * セッション一覧コンポーネント
 * 日付順にセッションを表示し、選択・削除を提供する
 */
export function SessionList({
  sessions,
  currentSessionId,
  onSelect,
  onDelete,
}: SessionListProps) {
  const [deleteTarget, setDeleteTarget] = useState<string | null>(null);

  const handleConfirmDelete = () => {
    if (deleteTarget) {
      onDelete(deleteTarget);
      setDeleteTarget(null);
    }
  };

  if (sessions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
        <MessageSquare className="h-8 w-8 mb-2" />
        <p className="text-sm">会話履歴がありません</p>
      </div>
    );
  }

  return (
    <>
      <div className="flex flex-col gap-1">
        {sessions.map((session) => (
          <div
            key={session.session_id}
            className={`group flex items-start gap-2 rounded-md p-3 cursor-pointer transition-colors hover:bg-accent ${
              currentSessionId === session.session_id
                ? "bg-accent border border-border"
                : ""
            }`}
            onClick={() => onSelect(session.session_id)}
          >
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium truncate">
                {session.preview || "新しい会話"}
              </p>
              <div className="flex items-center gap-2 mt-1">
                <span className="inline-flex items-center rounded-full bg-secondary px-2 py-0.5 text-xs text-secondary-foreground">
                  {session.model_name}
                </span>
                <span className="text-xs text-muted-foreground flex items-center gap-0.5">
                  <Clock className="h-3 w-3" />
                  {formatRelativeDate(session.updated_at)}
                </span>
                <span className="text-xs text-muted-foreground flex items-center gap-0.5">
                  <MessageSquare className="h-3 w-3" />
                  {session.message_count}
                </span>
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7 opacity-0 group-hover:opacity-100 shrink-0"
              onClick={(e) => {
                e.stopPropagation();
                setDeleteTarget(session.session_id);
              }}
            >
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </div>
        ))}
      </div>

      {/* 削除確認ダイアログ */}
      <Dialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>会話を削除しますか？</DialogTitle>
            <DialogDescription>
              この操作は取り消せません。会話履歴が完全に削除されます。
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              キャンセル
            </Button>
            <Button variant="destructive" onClick={handleConfirmDelete}>
              削除する
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}
