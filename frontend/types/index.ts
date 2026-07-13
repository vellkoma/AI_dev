// フロントエンドのTypeScript型定義

/** チャットメッセージ */
export interface Message {
  role: "user" | "assistant" | "system";
  content: string;
  timestamp?: number;
  metadata?: {
    usage?: { prompt_tokens: number; completion_tokens: number };
    response_time?: number;
    rag_sources?: RagSource[];
  };
}

/** RAG検索結果のソース情報 */
export interface RagSource {
  document: string;
  score: number;
  chunk_content: string;
}

/** LLMモデル情報 */
export interface ModelInfo {
  name: string;
  provider: string;
  status: "available" | "unavailable";
  parameters: Record<string, unknown>;
}

/** 会話セッションの概要 */
export interface SessionSummary {
  session_id: string;
  created_at: number;
  updated_at: number;
  message_count: number;
  model_name: string;
  preview: string;
}

/** 累積統計情報 */
export interface Stats {
  total_requests: number;
  total_tokens: number;
  average_response_time: number;
  estimated_cost: number;
}

/** アップロード済みドキュメント情報 */
export interface DocumentInfo {
  document_id: string;
  filename: string;
  content_type: string;
  chunk_count: number;
  uploaded_at: number;
  file_size: number;
}
