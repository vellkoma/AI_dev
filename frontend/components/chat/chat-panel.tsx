"use client";

import React, { useState, useRef, useCallback } from "react";
import { MessageList } from "@/components/chat/message-list";
import { MessageInput } from "@/components/chat/message-input";
import { streamChat } from "@/lib/sse";
import { Message } from "@/types";

interface ChatPanelProps {
  messages: Message[];
  onMessagesChange: (messages: Message[]) => void;
  ragEnabled?: boolean;
  sessionId?: string;
}

/** チャットパネル全体コンポーネント（メッセージリスト + 入力 + ストリーミング管理） */
export function ChatPanel({
  messages,
  onMessagesChange,
  ragEnabled = false,
  sessionId,
}: ChatPanelProps) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const abortControllerRef = useRef<AbortController | null>(null);

  const handleSend = useCallback(
    (content: string) => {
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
            // アシスタントメッセージを追加
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
          // エラーメッセージをアシスタントとして表示
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
    [messages, onMessagesChange, ragEnabled, sessionId]
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

      {/* 入力バー */}
      <MessageInput onSend={handleSend} disabled={isStreaming} />
    </div>
  );
}
