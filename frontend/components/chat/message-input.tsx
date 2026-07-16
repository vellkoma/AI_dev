"use client";

import React, { useState, useCallback, useRef, useEffect } from "react";
import { Plus, Send, X, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { api } from "@/lib/api";
import { cn } from "@/lib/utils";

interface AttachedFile {
  id: string;
  name: string;
  chunkCount: number;
}

interface MessageInputProps {
  onSend: (message: string, hasAttachment: boolean) => void;
  disabled?: boolean;
  /** 現在添付されているファイル一覧 */
  attachedFiles: AttachedFile[];
  /** ファイル添付時のコールバック */
  onFileAttach: (file: AttachedFile) => void;
  /** ファイル削除時のコールバック */
  onFileRemove: (fileId: string) => void;
}

/** メッセージ入力バーコンポーネント（+ボタンでファイル添付対応） */
export function MessageInput({
  onSend,
  disabled = false,
  attachedFiles,
  onFileAttach,
  onFileRemove,
}: MessageInputProps) {
  const [value, setValue] = useState("");
  const [uploading, setUploading] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  // テキストエリアの高さを内容に合わせて自動調整
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
    }
  }, [value]);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed, attachedFiles.length > 0);
    setValue("");
  }, [value, disabled, onSend, attachedFiles]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  // ファイルアップロード処理
  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const result = await api.rag.upload(file);
      if (result.success && result.document) {
        const attached: AttachedFile = {
          id: result.document.document_id,
          name: file.name,
          chunkCount: result.document.chunk_count,
        };
        onFileAttach(attached);
        toast({
          title: "ファイル添付完了",
          description: `${file.name} を添付しました`,
        });
      } else {
        toast({
          title: "アップロード失敗",
          description: result.message || "ファイルの処理に失敗しました",
          variant: "destructive",
        });
      }
    } catch {
      toast({
        title: "アップロードエラー",
        description: "サーバーとの通信に失敗しました",
        variant: "destructive",
      });
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  // ファイル削除処理
  const handleRemoveFile = async (fileId: string) => {
    try {
      await api.rag.delete(fileId);
    } catch {
      // 削除失敗してもUIからは除去する
    }
    onFileRemove(fileId);
  };

  return (
    <div className="border-t p-4">
      {/* 添付ファイルバッジ */}
      {attachedFiles.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2">
          {attachedFiles.map((file) => (
            <div
              key={file.id}
              className="flex items-center gap-1 px-2 py-1 rounded-md bg-muted text-sm"
            >
              <FileText className="h-3 w-3" />
              <span className="max-w-[150px] truncate">{file.name}</span>
              <button
                onClick={() => handleRemoveFile(file.id)}
                className="ml-1 hover:text-destructive"
                aria-label={`${file.name}を削除`}
              >
                <X className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 入力バー */}
      <div className="flex gap-2 items-end">
        {/* +ボタン（ファイル添付） */}
        <Button
          variant="ghost"
          size="icon"
          onClick={() => fileInputRef.current?.click()}
          disabled={disabled || uploading}
          aria-label="ファイルを添付"
          className="shrink-0"
        >
          <Plus className="h-5 w-5" />
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".txt,.md,.pdf"
          onChange={handleFileUpload}
          className="hidden"
        />

        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            uploading
              ? "アップロード中..."
              : "メッセージを入力... (Shift+Enterで改行)"
          }
          disabled={disabled || uploading}
          rows={1}
          className={cn(
            "flex-1 resize-none rounded-md border border-input bg-background px-3 py-2 text-sm",
            "ring-offset-background placeholder:text-muted-foreground",
            "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
            "disabled:cursor-not-allowed disabled:opacity-50",
            "min-h-[40px] max-h-[150px]"
          )}
          aria-label="メッセージ入力"
        />
        <Button
          onClick={handleSend}
          disabled={disabled || uploading || !value.trim()}
          size="icon"
          aria-label="送信"
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
