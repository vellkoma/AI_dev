# Phase 2: Next.js フロントエンド

LLMチャットダッシュボード。Tailwind CSS + shadcn/uiによるプロフェッショナルなUI。

## 機能

- SSEストリーミングチャット（Markdownレンダリング対応）
- モデル切り替え（OpenAI / Claude / Gemini）
- RAGモード（ドキュメントアップロード・検索拡張）
- 統計ダッシュボード（トークン使用量、コスト、時系列グラフ）
- 会話履歴管理（一覧・検索・削除）
- ダーク/ライトモード切り替え
- レスポンシブデザイン（デスクトップ・タブレット対応）

## セットアップ

```bash
cd frontend

# 依存パッケージのインストール
npm install

# 環境変数の設定
# .env.local ファイルを作成
echo NEXT_PUBLIC_API_URL=http://localhost:8000 > .env.local

# 開発サーバー起動
npm run dev
```

開発サーバーは `http://localhost:3000` で起動する。

## ビルド

```bash
# プロダクションビルド
npm run build

# ビルド結果の確認
npm run start
```

## 環境変数

| 変数名 | 説明 | デフォルト |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | バックエンドAPIのベースURL | http://localhost:8000 |

## ディレクトリ構造

```
frontend/
├── app/
│   ├── layout.tsx         # ルートレイアウト（テーマ・トースト設定）
│   ├── page.tsx           # ダッシュボードメインページ
│   └── globals.css        # グローバルスタイル
├── components/
│   ├── ui/                # shadcn/uiベースコンポーネント
│   ├── chat/              # チャットUI（メッセージリスト、入力バー）
│   ├── sidebar/           # サイドバー（モデル選択、RAGトグル）
│   ├── stats/             # 統計パネル（カード、チャート）
│   ├── history/           # 会話履歴（一覧、検索）
│   └── layout/            # レイアウトコンポーネント
├── lib/
│   ├── api.ts             # REST APIクライアント
│   ├── sse.ts             # SSEストリーミングクライアント
│   └── utils.ts           # ユーティリティ関数
├── types/
│   └── index.ts           # TypeScript型定義
└── package.json
```

## 技術スタック

- **フレームワーク**: Next.js 14+（App Router）
- **言語**: TypeScript
- **スタイリング**: Tailwind CSS + shadcn/ui
- **グラフ**: recharts
- **Markdownレンダリング**: react-markdown + remark-gfm
- **テーマ**: next-themes（ダーク/ライトモード）
- **アイコン**: lucide-react
