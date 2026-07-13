# Phase 1: LLM Chat App (CLI版)

商用LLM APIとローカルモデルの2つのアプローチによるチャットアプリケーション

## 概要

本モジュールは、LLM技術の基礎を習得するためのCLI版チャットアプリケーションです。以下の2つのアプローチを実装しています：

1. **API_Chat_Client**: 商用LLM API（OpenAI / Claude / Gemini）を使用
2. **Local_Chat_Client**: オープンソースLLMモデルをローカルで実行

## 機能一覧

| 機能 | 説明 |
|------|------|
| 商用API対応 | OpenAI、Claude、Gemini の3プロバイダー対応 |
| ローカルモデル対応 | llama-cpp-python / Ollama によるローカルLLM実行 |
| ストリーミング表示 | レスポンスをリアルタイムに逐次表示 |
| 会話履歴管理 | メモリ内の会話履歴保持・トークン制限による自動削減 |
| 会話の永続化 | JSON形式での会話履歴の保存・読み込み |
| パフォーマンス統計 | 応答時間、トークン数、推定コストの表示 |
| 設定管理 | YAML形式の設定ファイルによる柔軟な設定 |
| ログ機能 | API呼び出し、エラー、パフォーマンス指標のログ記録 |

## アーキテクチャ

```
┌─────────────────────────────────────────────────┐
│           Presentation Layer (CLI)              │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────┐
│           Application Layer                     │
│   ChatOrchestrator + Command Processor          │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────┐
│           Domain Layer                          │
│  BaseLLMClient │ History_Manager │ Stream_Handler│
│  (API/Local)   │                │               │
└─────────────────────┬───────────────────────────┘
                      │
┌─────────────────────┴───────────────────────────┐
│           Infrastructure Layer                  │
│  Config_Manager │ Logger │ Persistence (JSON)   │
└─────────────────────────────────────────────────┘
```

## 使用方法

```bash
# APIモードで起動
python -m llm_chat_app.main --mode api

# プロバイダー指定
python -m llm_chat_app.main --mode api --provider openai
python -m llm_chat_app.main --mode api --provider claude
python -m llm_chat_app.main --mode api --provider gemini

# ローカルモードで起動
python -m llm_chat_app.main --mode local
```

### チャットコマンド

| コマンド | 説明 |
|----------|------|
| `/clear` | 会話履歴をクリア |
| `/save [ファイル名]` | 会話履歴をJSONファイルに保存 |
| `/load <ファイル名>` | 保存済みの会話履歴を読み込み |
| `/stats` | パフォーマンス統計を表示 |
| `/help` | コマンド一覧を表示 |
| `/exit` | アプリケーションを終了 |

## ディレクトリ構成

```
llm_chat_app/
├── __init__.py
├── main.py              # エントリーポイント
├── models.py            # データモデル（Message, LLMResponse, Conversation）
├── exceptions.py        # カスタム例外クラス
├── clients/             # LLMクライアント実装
│   ├── base.py          # BaseLLMClient（抽象基底クラス）
│   ├── api_client.py    # API_Chat_Client
│   └── local_client.py  # Local_Chat_Client
├── core/                # コア機能
│   ├── history.py       # History_Manager
│   ├── stream.py        # Stream_Handler
│   └── orchestrator.py  # ChatOrchestrator
├── infrastructure/      # インフラ層
│   ├── config.py        # Config_Manager
│   └── logger.py        # ロガー設定
└── ui/                  # ユーザーインターフェース
    └── cli.py           # Chat_Interface（CLI）
```

## テスト

```bash
# 全テスト実行
pytest tests/ -v

# プロパティベーステスト
pytest tests/property_tests/ -v

# カバレッジ
pytest --cov=llm_chat_app --cov-report=term-missing
```

## 設定ファイル

`config.yaml` で以下を管理：

- APIプロバイダーとモデル名
- API_Key（環境変数展開 `${OPENAI_API_KEY}` 対応）
- 温度パラメータ、最大トークン数
- ローカルモデルのパスとパラメータ
- ログ設定

サンプル: [`config.yaml.example`](../config.yaml.example)

## 関連ドキュメント

- [環境構築手順](../docs/SETUP.md)
- [API_Key設定ガイド](../docs/API_SETUP.md)
- [ローカルモデルセットアップ](../docs/LOCAL_MODEL_SETUP.md)
