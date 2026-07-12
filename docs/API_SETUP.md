# API_Key 設定ガイド

本ドキュメントでは、各LLM APIプロバイダーのAPI_Key取得方法と設定方法を説明します。

## 目次

1. [OpenAI API_Key の取得と設定](#openai-api_key-の取得と設定)
2. [Anthropic Claude API_Key の取得と設定](#anthropic-claude-api_key-の取得と設定)
3. [Google Gemini API_Key の取得と設定](#google-gemini-api_key-の取得と設定)
4. [config.yaml への設定方法](#configyaml-への設定方法)
5. [環境変数での設定方法](#環境変数での設定方法)

---

## OpenAI API_Key の取得と設定

### 手順1: アカウント作成

1. [OpenAI Platform](https://platform.openai.com/) にアクセスする
2. 「Sign Up」をクリックしてアカウントを作成する（Google/Microsoft アカウントでも可）
3. メールアドレスの確認を完了する

### 手順2: API_Key の発行

1. [API Keys ページ](https://platform.openai.com/api-keys) にアクセスする
2. 「Create new secret key」をクリックする
3. キーの名前を入力する（例: `llm-chat-app`）
4. 表示されたAPI_Keyをコピーする

> ⚠️ **注意**: API_Keyは作成時にのみ表示されます。必ずコピーして安全な場所に保存してください。

### 手順3: 課金設定

1. [Billing ページ](https://platform.openai.com/account/billing/overview) にアクセスする
2. 支払い方法を登録する（クレジットカード）
3. 使用量制限を設定する（月額上限の設定を推奨）

### 利用可能なモデル

| モデル名 | 説明 | 推奨用途 |
|----------|------|----------|
| `gpt-3.5-turbo` | コスト効率が高い | 開発・テスト |
| `gpt-4` | 高品質な応答 | 本番利用 |
| `gpt-4-turbo` | 高速・高品質 | 本番利用 |

---

## Anthropic Claude API_Key の取得と設定

### 手順1: アカウント作成

1. [Anthropic Console](https://console.anthropic.com/) にアクセスする
2. 「Sign Up」をクリックしてアカウントを作成する
3. メールアドレスの確認を完了する

### 手順2: API_Key の発行

1. [API Keys ページ](https://console.anthropic.com/settings/keys) にアクセスする
2. 「Create Key」をクリックする
3. キーの名前を入力する（例: `llm-chat-app`）
4. 表示されたAPI_Keyをコピーする

> ⚠️ **注意**: API_Keyは作成時にのみ表示されます。必ずコピーして安全な場所に保存してください。

### 手順3: 課金設定

1. [Plans & Billing ページ](https://console.anthropic.com/settings/plans) にアクセスする
2. 適切なプランを選択する
3. 支払い方法を登録する

### 利用可能なモデル

| モデル名 | 説明 | 推奨用途 |
|----------|------|----------|
| `claude-3-haiku-20240307` | 高速・低コスト | 開発・テスト |
| `claude-3-sonnet-20240229` | バランス型 | 一般利用 |
| `claude-3-opus-20240229` | 最高品質 | 高度なタスク |

---

## Google Gemini API_Key の取得と設定

### 手順1: Google AI Studio へアクセス

1. [Google AI Studio](https://aistudio.google.com/) にアクセスする
2. Google アカウントでログインする

### 手順2: API_Key の発行

1. [API Keys ページ](https://aistudio.google.com/app/apikey) にアクセスする
2. 「Create API Key」をクリックする
3. プロジェクトを選択する（または新規作成）
4. 表示されたAPI_Keyをコピーする

### 手順3: 課金設定（無料枠あり）

- Gemini API には無料枠があります（制限あり）
- 無料枠を超える場合は [Google Cloud Console](https://console.cloud.google.com/) で課金設定を行う

### 利用可能なモデル

| モデル名 | 説明 | 推奨用途 |
|----------|------|----------|
| `gemini-pro` | 標準モデル | 一般利用 |
| `gemini-1.5-pro` | 高性能・長文対応 | 長い会話 |

---

## config.yaml への設定方法

`config.yaml.example` をコピーして `config.yaml` を作成し、API_Keyを設定します。

```bash
copy config.yaml.example config.yaml
```

### OpenAI を使用する場合

```yaml
api:
  provider: "openai"
  api_key: "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  model: "gpt-3.5-turbo"
```

### Claude を使用する場合

```yaml
api:
  provider: "claude"
  api_key: "sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  model: "claude-3-haiku-20240307"
```

### Gemini を使用する場合

```yaml
api:
  provider: "gemini"
  api_key: "AIzaxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  model: "gemini-pro"
```

### 環境変数を参照する場合

API_Keyを直接設定ファイルに書かず、環境変数から読み込むこともできます。

```yaml
api:
  provider: "openai"
  api_key: "${OPENAI_API_KEY}"
  model: "gpt-3.5-turbo"
```

---

## 環境変数での設定方法

セキュリティの観点から、API_Keyは環境変数で管理することを推奨します。

### Windows（コマンドプロンプト）

```cmd
set OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
set ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
set GOOGLE_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### Windows（PowerShell）

```powershell
$env:OPENAI_API_KEY = "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$env:ANTHROPIC_API_KEY = "sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
$env:GOOGLE_API_KEY = "AIzaxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
```

### 永続的に設定する場合（Windows）

1. 「スタートメニュー」→「設定」→「システム」→「バージョン情報」→「システムの詳細設定」
2. 「環境変数」をクリック
3. 「ユーザー環境変数」で「新規」をクリック
4. 変数名と値を入力して「OK」

### .env ファイルを使用する場合

プロジェクトルートに `.env` ファイルを作成して管理することもできます。

```bash
# .env
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_API_KEY=AIzaxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

> ⚠️ **重要**: `.env` ファイルは `.gitignore` に含まれていることを確認してください。API_Keyを Git にコミットしないでください。

---

## セキュリティに関する注意事項

- API_Keyはパスワードと同様に扱い、他者と共有しないでください
- API_Keyをソースコードに直接記述しないでください
- `config.yaml` と `.env` は `.gitignore` に含めてください
- 定期的にAPI_Keyをローテーション（再発行）することを推奨します
- 各プロバイダーの使用量制限を設定し、予期しない課金を防いでください
