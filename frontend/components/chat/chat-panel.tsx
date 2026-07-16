"use client";

import React, { useState, useRef, useCallback } from "react";
import { MessageList } from "@/components/chat/message-list";
import { MessageInput } from "@/components/chat/message-input";
import { streamChat } from "@/lib/sse";
import { Message } from "@/types";

interface AttachedFile {
  id: string;
  name: string;
  chunkCount: number;
}

interface ChatPanelProps {
  messages: Message[];
  onMessagesChange: (messages: Message[]) => void;
  sessionId?: string;
}

/** チャットパネル全体コンポーネント（メッセージリスト + 入力 + ストリーミング管理） */
export function ChatPanel({
  messages,
  onMessagesChange,
  sessionId,
}: ChatPanelProps) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [attachedFiles, setAttachedFiles] = useState<AttachedFile[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleFileAttach = useCallback((file: AttachedFile) => {
    setAttachedFiles((prev) => [...prev, file]);
  }, []);

  const handleFileRemove = useCallback((fileId: string) => {
    setAttachedFiles((prev) => prev.filter((f) => f.id !== fileId));
  }, []);

  const handleSend = useCallback(
    (content: string, hasAttachment: boolean) => {
      // ユーザーメッセージを追加
      const userMessage: Message = {
        role: "user",
        content,
        timestamp: Date.now(),
      };
      const updatedMessages = [...messages, userMessage];
      onMessagesChange(updatedMessages);

      // ストリーミング開始
      setIsStreaming(true);
      setStreamingContent("");

      // ファイルが添付されている場合はRAGを有効にする
      const ragEnabled = hasAttachment || attachedFiles.length > 0;

      const controller = streamChat({
        message: content,
        history: updatedMessages,
        ragEnabled,
        sessionId,
        onToken: (token) => {
          setStreamingContent((prev) => prev + token);
        },
        onDone: (metadata) => {
          setIsStreaming(false);
          setStreamingContent((prev) => {
            const assistantMessage: Message = {
              role: "assistant",
              content: prev,
              timestamp: Date.now(),
              metadata: metadata
                ? {
                    usage: metadata.usage,
                    response_time: metadata.response_time,
                    rag_sources: metadata.rag_sources?.map((s) => ({
                      document: s.document,
                      score: s.score,
                      chunk_content: "",
                    })),
                  }
                : undefined,
            };
            onMessagesChange([...updatedMessages, assistantMessage]);
            return "";
          });
        },
        onError: (error) => {
          setIsStreaming(false);
          setStreamingContent("");
          const errorMessage: Message = {
            role: "assistant",
            content: `エラーが発生しました: ${error}`,
            timestamp: Date.now(),
          };
          onMessagesChange([...updatedMessages, errorMessage]);
        },
      });

      abortControllerRef.current = controller;
    },
    [messages, onMessagesChange, attachedFiles, sessionId]
  );

  return (
    <div className="flex flex-col h-full">
      {/* メッセージリスト */}
      <div className="flex-1 overflow-hidden">
        <MessageList
          messages={messages}
          streamingContent={streamingContent}
          isStreaming={isStreaming}
        />
      </div>

      {/* ストリーミングインジケーター */}
      {isStreaming && (
        <div className="px-4 py-1 text-xs text-muted-foreground border-t bg-muted/50">
          ストリーミング中...
        </div>
      )}

      {/* 入力バー（+ボタン付き） */}
      <MessageInput
        onSend={handleSend}
        disabled={isStreaming}
        attachedFiles={attachedFiles}
        onFileAttach={handleFileAttach}
        onFileRemove={handleFileRemove}
      />
    </div>
  );
}
