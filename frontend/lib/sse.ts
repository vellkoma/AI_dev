/**
 * SSEストリーミングクライアント
 * バックエンドのチャットAPIからServer-Sent Eventsでトークンを受信する
 */

import { Message } from "@/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/** SSEストリーミング完了時のメタデータ */
interface StreamMetadata {
  usage?: { prompt_tokens: number; completion_tokens: number };
  response_time?: number;
  rag_sources?: Array<{ document: string; score: number }>;
}

/** streamChat関数のオプション */
interface StreamChatOptions {
  message: string;
  history: Message[];
  ragEnabled: boolean;
  sessionId?: string;
  onToken: (token: string) => void;
  onDone: (metadata: StreamMetadata) => void;
  onError: (error: string) => void;
}

/**
 * SSEストリーミングでチャットメッセージを送信する
 * AbortControllerを返すため、呼び出し側でストリーミングをキャンセルできる
 */
export function streamChat(options: StreamChatOptions): AbortController {
  const { message, history, ragEnabled, sessionId, onToken, onDone, onError } =
    options;
  const controller = new AbortController();

  const body = JSON.stringify({
    message,
    history: history.map((m) => ({ role: m.role, content: m.content })),
    rag_enabled: ragEnabled,
    session_id: sessionId || null,
  });

  fetch(`${BASE_URL}/api/chat/send`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body,
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        onError(`HTTP ${response.status}: ${response.statusText}`);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        onError("Response body is not readable");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          // イベントタイプ行はスキップ
          if (line.startsWith("event: ")) {
            continue;
          }
          // データ行を処理
          if (line.startsWith("data: ")) {
            const dataStr = line.slice(6);
            try {
              const data = JSON.parse(dataStr);
              if ("token" in data) {
                onToken(data.token);
              } else if ("message" in data && "metadata" in data) {
                onDone(data.metadata || {});
              } else if ("error" in data) {
                onError(data.error);
              }
            } catch {
              // 空のデータ行やパースエラーは無視
            }
          }
        }
      }
    })
    .catch((err) => {
      if (err.name !== "AbortError") {
        onError(err.message || "Unknown error");
      }
    });

  return controller;
}
