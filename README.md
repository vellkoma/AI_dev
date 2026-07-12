# LLM Chat App

LLM API入門ポートフォリオプロジェクト — 商用APIとローカルモデルの2つのアプローチによるチャットアプリケーション

## プロジェクト概要

本プロジェクトは、LLM（大規模言語モデル）技術の基礎を習得するためのチャットアプリケーションです。以下の2つの異なるアプローチでLLMチャットを実装し、それぞれの特性を比較・学習できます。

1. **API_Chat_Client**: 商用LLM API（OpenAI / Claude / Gemini）を使用するアプローチ
2. **Local_Chat_Client**: オープンソースLLMモデルをローカルで実行するアプローチ

## 機能一覧

| 機能 | 説明 |
|------|------|
| 商用API対応 | OpenAI、Claude、Gemini の3つのAPIプロバイダーに対応 |
| ローカルモデル対応 | llama-cpp-python / Ollama によるローカルLLM実行 |
| ストリーミング表示 | レスポンスをリアルタイムに逐次表示 |
| 会話履歴管理 | メモリ内の会話履歴保持・トークン制限による自動削減 |
| 会話の永続化 | JSON形式での会話履歴の保存・読み込み |
| パフォーマンス統計 | 応答時間、トークン数、推定コストの表示 |
| 設定管理 | YAML形式の設定ファイルによる柔軟な設定 |
| ログ機能 | API呼び出し、エラー、パフォーマンス指標のログ記録 |

## 技術スタック

- **言語**: Python 3.9+
- **LLM API SDK**:
  - OpenAI Python SDK (`openai>=1.0.0`)
  - Anthropic Python SDK (`anthropic>=0.7.0`)
  - Google Generative AI SDK (`google-generativeai>=0.3.0`)
- **ローカルモデル実行**: `llama-cpp-python>=0.2.0`
- **設定管理**: `pyyaml>=6.0`
- **テスト**: pytest, pytest-mock, hypothesis
- **コード品質**: black, flake8, isort, mypy

## クイックスタート

```bash
# リポジトリのクローン
git clone https://github.com/your-username/llm-chat-app.git
cd llm-chat-app

# 仮想環境の作成と有効化
python -m venv .venv
.venv\Scripts\activate  # Windows

# 依存関係のインストール
pip install -r requirements.txt

# 設定ファイルの作成
copy config.yaml.example config.yaml
# config.yaml を編集してAPI_Keyを設定

# アプリケーションの起動（APIモード）
python -m llm_chat_app.main --mode api

# アプリケーションの起動（ローカルモデルモード）
python -m llm_chat_app.main --mode local
```

詳細なセットアップ手順は [docs/SETUP.md](docs/SETUP.md) を参照してください。

## 使用方法

### APIモードでの起動

```bash
# デフォルト（config.yamlの設定を使用）
python -m llm_chat_app.main --mode api

# プロバイダーを指定して起動
python -m llm_chat_app.main --mode api --provider openai
python -m llm_chat_app.main --mode api --provider claude
python -m llm_chat_app.main --mode api --provider gemini
```

### ローカルモードでの起動

```bash
# デフォルト（config.yamlの設定を使用）
python -m llm_chat_app.main --mode local

# モデルパスを指定して起動
python -m llm_chat_app.main --mode local --model-path ./models/your-model.gguf
```

### 主なコマンド

チャット中に使用できるコマンド一覧：

| コマンド | 説明 |
|----------|------|
| `/clear` | 会話履歴をクリア |
| `/save [ファイル名]` | 会話履歴をJSONファイルに保存 |
| `/load <ファイル名>` | 保存済みの会話履歴を読み込み |
| `/stats` | パフォーマンス統計（応答時間、トークン数、推定コスト）を表示 |
| `/help` | 利用可能なコマンド一覧を表示 |
| `/exit` | アプリケーションを終了 |

## プロジェクト構造

```
llm-chat-app/
├── llm_chat_app/            # メインパッケージ
│   ├── __init__.py
│   ├── main.py              # エントリーポイント
│   ├── models.py            # データモデル（Message, LLMResponse, Conversation）
│   ├── exceptions.py        # カスタム例外クラス
│   ├── clients/             # LLMクライアント実装
│   │   ├── __init__.py
│   │   ├── base.py          # BaseLLMClient（抽象基底クラス）
│   │   ├── api_client.py    # API_Chat_Client
│   │   └── local_client.py  # Local_Chat_Client
│   ├── core/                # コア機能
│   │   ├── __init__.py
│   │   ├── history.py       # History_Manager
│   │   └── stream.py        # Stream_Handler
│   ├── infrastructure/      # インフラ層
│   │   ├── __init__.py
│   │   ├── config.py        # Config_Manager
│   │   └── logger.py        # ロガー設定
│   └── ui/                  # ユーザーインターフェース
│       ├── __init__.py
│       └── chat_interface.py # Chat_Interface（CLI）
├── tests/                   # テスト
│   ├── __init__.py
│   ├── test_config.py
│   ├── test_history.py
│   ├── test_stream.py
│   └── property_tests/      # プロパティベーステスト
├── docs/                    # ドキュメント
│   ├── API_SETUP.md         # API_Key設定ガイド
│   ├── LOCAL_MODEL_SETUP.md # ローカルモデルセットアップガイド
│   └── SETUP.md             # 環境構築手順
├── conversations/           # 会話履歴保存先
├── logs/                    # ログファイル保存先
├── models/                  # ローカルモデル保存先
├── config.yaml.example      # 設定ファイルサンプル
├── pyproject.toml           # プロジェクト設定
├── requirements.txt         # 依存関係
└── README.md                # 本ファイル
```

## テスト実行方法

```bash
# 全テストの実行
pytest

# 詳細出力で実行
pytest -v

# 特定のテストファイルを実行
pytest tests/test_history.py

# プロパティベーステストのみ実行
pytest tests/property_tests/

# カバレッジレポート付きで実行
pytest --cov=llm_chat_app --cov-report=term-missing
```

### コード品質チェック

```bash
# フォーマッター
black llm_chat_app tests

# import整理
isort llm_chat_app tests

# リンター
flake8 llm_chat_app tests

# 型チェック
mypy llm_chat_app
```

## ドキュメント

- [環境構築手順 (SETUP.md)](docs/SETUP.md)
- [API_Key設定ガイド (API_SETUP.md)](docs/API_SETUP.md)
- [ローカルモデルセットアップ (LOCAL_MODEL_SETUP.md)](docs/LOCAL_MODEL_SETUP.md)

## ライセンス

MIT License
