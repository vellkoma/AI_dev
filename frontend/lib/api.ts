/**
 * REST APIクライアント
 * バックエンドのFastAPI各エンドポイントへのアクセスを提供する
 */

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const api = {
  /** モデル管理API */
  models: {
    /** 利用可能モデル一覧を取得 */
    list: () => fetch(`${BASE_URL}/api/models`).then((r) => r.json()),
    /** モデルを切り替え */
    switch: (model: string, provider: string) =>
      fetch(`${BASE_URL}/api/models/switch`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model, provider }),
      }).then((r) => r.json()),
  },

  /** 会話履歴API */
  history: {
    /** セッション一覧を取得 */
    list: () => fetch(`${BASE_URL}/api/history/sessions`).then((r) => r.json()),
    /** セッション詳細を取得 */
    get: (id: string) =>
      fetch(`${BASE_URL}/api/history/sessions/${id}`).then((r) => r.json()),
    /** 新規セッションを作成 */
    create: (modelName?: string) =>
      fetch(
        `${BASE_URL}/api/history/sessions${modelName ? `?model_name=${modelName}` : ""}`,
        { method: "POST" }
      ).then((r) => r.json()),
    /** セッションを削除 */
    delete: (id: string) =>
      fetch(`${BASE_URL}/api/history/sessions/${id}`, { method: "DELETE" }),
    /** キーワードでセッションを検索 */
    search: (keyword: string) =>
      fetch(
        `${BASE_URL}/api/history/search?keyword=${encodeURIComponent(keyword)}`
      ).then((r) => r.json()),
  },

  /** 統計API */
  stats: {
    /** 累積統計を取得 */
    get: () => fetch(`${BASE_URL}/api/stats`).then((r) => r.json()),
    /** モデル別統計を取得 */
    byModel: () =>
      fetch(`${BASE_URL}/api/stats/by-model`).then((r) => r.json()),
    /** 時系列統計を取得 */
    timeline: (period: string) =>
      fetch(`${BASE_URL}/api/stats/timeline?period=${period}`).then((r) =>
        r.json()
      ),
  },

  /** RAGドキュメント管理API */
  rag: {
    /** ドキュメントをアップロード */
    upload: (file: File) => {
      const formData = new FormData();
      formData.append("file", file);
      return fetch(`${BASE_URL}/api/rag/documents/upload`, {
        method: "POST",
        body: formData,
      }).then((r) => r.json());
    },
    /** アップロード済みドキュメント一覧を取得 */
    list: () =>
      fetch(`${BASE_URL}/api/rag/documents`).then((r) => r.json()),
    /** ドキュメントを削除 */
    delete: (id: string) =>
      fetch(`${BASE_URL}/api/rag/documents/${id}`, { method: "DELETE" }),
  },

  /** ヘルスチェックAPI */
  health: {
    /** バックエンド接続状態を確認 */
    check: () =>
      fetch(`${BASE_URL}/health`)
        .then((r) => r.json())
        .catch(() => ({ status: "unhealthy" })),
  },
};
