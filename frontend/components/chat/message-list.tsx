"use client";

import React, { useCallback, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Check, User, Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { Message } from "@/types";

interface MessageListProps {
  messages: Message[];
  streamingContent?: string;
  isStreaming?: boolean;
}

/** 単一メッセージの表示コンポーネント */
function MessageBubble({ message }: { message: Message }) {
  const [copied, setCopied] = React.useState(false);
  const isUser = message.role === "user";

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [message.content]);

  return (
    <div
      className={cn(
        "flex gap-3 w-full",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {/* アシスタントアイコン */}
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
          <Bot className="w-4 h-4" />
        </div>
      )}

      <div
        className={cn(
          "relative group max-w-[80%] rounded-lg px-4 py-3",
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground"
        )}
      >
        {/* メッセージ内容 */}
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm">{message.content}</p>
        ) : (
          <div className="prose prose-sm dark:prose-invert max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* コピーボタン */}
        <Button
          variant="ghost"
          size="icon"
          className={cn(
            "absolute -top-2 -right-2 h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity",
            "bg-background border shadow-sm"
          )}
          onClick={handleCopy}
          aria-label="メッセージをコピー"
        >
          {copied ? (
            <Check className="h-3 w-3 text-green-500" />
          ) : (
            <Copy className="h-3 w-3" />
          )}
        </Button>

        {/* メタデータ表示（トークン使用量・応答時間） */}
        {message.metadata && (
          <div className="mt-2 pt-2 border-t border-border/50 text-xs text-muted-foreground flex gap-3">
            {message.metadata.usage && (
              <span>
                トークン: {message.metadata.usage.prompt_tokens + message.metadata.usage.completion_tokens}
              </span>
            )}
            {message.metadata.response_time != null && (
              <span>応答: {message.metadata.response_time.toFixed(2)}s</span>
            )}
          </div>
        )}
      </div>

      {/* ユーザーアイコン */}
      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary flex items-center justify-center">
          <User className="w-4 h-4 text-primary-foreground" />
        </div>
      )}
    </div>
  );
}

/** メッセージリストコンポーネント（自動スクロール付き） */
export function MessageList({
  messages,
  streamingContent,
  isStreaming,
}: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // 新しいメッセージやストリーミング更新時に自動スクロール
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  return (
    <ScrollArea className="flex-1 p-4">
      <div className="space-y-4">
        {messages.map((msg, index) => (
          <MessageBubble key={index} message={msg} />
        ))}

        {/* ストリーミング中のメッセージ */}
        {isStreaming && streamingContent && (
          <div className="flex gap-3 justify-start">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
              <Bot className="w-4 h-4" />
            </div>
            <div className="max-w-[80%] rounded-lg px-4 py-3 bg-muted text-foreground">
              <div className="prose prose-sm dark:prose-invert max-w-none">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {streamingContent}
                </ReactMarkdown>
              </div>
            </div>
          </div>
        )}

        {/* ローディングインジケーター */}
        {isStreaming && !streamingContent && (
          <div className="flex gap-3 justify-start">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
              <Bot className="w-4 h-4" />
            </div>
            <div className="rounded-lg px-4 py-3 bg-muted">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-foreground/50 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                <span className="w-2 h-2 bg-foreground/50 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                <span className="w-2 h-2 bg-foreground/50 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          </div>
        )}

        {/* 自動スクロール用アンカー */}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
