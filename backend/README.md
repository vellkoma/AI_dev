# Phase 2: FastAPI バックエンド

LLMチャットアプリケーションのWeb APIバックエンド。SSEストリーミング、RAG、統計機能を提供する。

## APIエンドポイント一覧

| エンドポイント | メソッド | 説明 |
|---|---|---|
| `/api/chat/send` | POST | SSEストリーミングでチャットレスポンスを配信 |
| `/api/models` | GET | 利用可能なモデル一覧 |
| `/api/models/switch` | POST | モデル切り替え |
| `/api/history/sessions` | GET/POST | セッション一覧/作成 |
| `/api/history/sessions/{id}` | GET/DELETE | セッション詳細/削除 |
| `/api/history/search` | GET | キーワード検索 |
| `/api/stats` | GET | 累積統計 |
| `/api/stats/by-model` | GET | モデル別統計 |
| `/api/stats/timeline` | GET | 時系列統計 |
| `/api/rag/documents/upload` | POST | ドキュメントアップロード |
| `/api/rag/documents` | GET | ドキュメント一覧 |
| `/api/rag/documents/{id}` | DELETE | ドキュメント削除 |

## 環境変数

| 変数名 | 説明 | デフォルト |
|---|---|---|
| `OPENAI_API_KEY` | OpenAI APIキー | - |
| `ANTHROPIC_API_KEY` | Anthropic APIキー | - |
| `GEMINI_API_KEY` | Gemini APIキー | - |
| `DEFAULT_PROVIDER` | デフォルトプロバイダー | openai |
| `DEFAULT_MODEL` | デフォルトモデル | gpt-3.5-turbo |
| `BACKEND_PORT` | サーバーポート | 8000 |
| `CORS_ORIGINS` | CORS許可オリジン | http://localhost:3000 |
| `CHROMA_PERSIST_DIR` | ChromaDB永続化ディレクトリ | ./data/chroma |
| `EMBEDDING_MODEL` | 埋め込みモデル名 | all-MiniLM-L6-v2 |

## セットアップ

```bash
# 仮想環境の作成・有効化
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# 依存パッケージのインストール
pip install -r backend/requirements.txt

# 環境変数の設定（.envファイルまたはシェル変数）
set OPENAI_API_KEY=your-api-key
set DEFAULT_PROVIDER=openai
set DEFAULT_MODEL=gpt-3.5-turbo

# サーバー起動
uvicorn backend.app.main:app --reload --port 8000
```

起動後、`http://localhost:8000/docs` でSwagger UIが表示される。

## テスト実行

```bash
# 全テスト
pytest backend/tests/ -v

# プロパティベーステスト
pytest backend/tests/property_tests/ -v
```

## ディレクトリ構造

```
backend/
├── app/
│   ├── main.py            # FastAPIアプリエントリポイント
│   ├── config.py          # 設定管理（環境変数読み込み）
│   ├── dependencies.py    # 依存性注入
│   ├── routers/           # APIルーター
│   │   ├── chat.py        # チャット（SSEストリーミング）
│   │   ├── models.py      # モデル管理
│   │   ├── history.py     # 会話履歴CRUD
│   │   ├── stats.py       # 統計API
│   │   └── rag.py         # RAGドキュメント管理
│   ├── services/          # ビジネスロジック
│   │   ├── llm_service.py
│   │   ├── rag_service.py
│   │   ├── session_service.py
│   │   └── stats_service.py
│   ├── schemas/           # Pydanticスキーマ
│   │   ├── chat.py
│   │   ├── models.py
│   │   ├── history.py
│   │   ├── stats.py
│   │   └── rag.py
│   └── rag/               # RAGエンジン
│       ├── document_loader.py
│       ├── chunker.py
│       └── embeddings.py
├── tests/
│   ├── property_tests/    # プロパティベーステスト
│   └── ...                # ユニット/統合テスト
└── requirements.txt
```

## 技術スタック

- **フレームワーク**: FastAPI + uvicorn
- **ストリーミング**: sse-starlette（Server-Sent Events）
- **スキーマ**: Pydantic v2
- **RAG**: LangChain + ChromaDB + sentence-transformers
- **テスト**: pytest + Hypothesis（プロパティベーステスト）
