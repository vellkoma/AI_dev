# 環境構築手順

本ドキュメントでは、LLM Chat App を動作させるための環境構築手順を説明します。

## 目次

1. [Python のインストール](#python-のインストール)
2. [リポジトリのクローン](#リポジトリのクローン)
3. [仮想環境の作成と有効化](#仮想環境の作成と有効化)
4. [依存関係のインストール](#依存関係のインストール)
5. [設定ファイルの作成](#設定ファイルの作成)
6. [動作確認](#動作確認)

---

## Python のインストール

### 要件

- Python 3.9 以上が必要です

### インストール手順（Windows）

1. [Python 公式サイト](https://www.python.org/downloads/) にアクセスする
2. 最新の Python 3.x（3.9以上）をダウンロードする
3. インストーラーを実行する

> ⚠️ **重要**: インストール時に **「Add Python to PATH」にチェックを入れてください**

4. インストール完了後、コマンドプロンプトでバージョンを確認する

```bash
python --version
```

出力例:
```
Python 3.11.7
```

### pip の確認

```bash
pip --version
```

pip がインストールされていない場合:
```bash
python -m ensurepip --upgrade
```

---

## リポジトリのクローン

### Git がインストール済みの場合

```bash
git clone https://github.com/your-username/llm-chat-app.git
cd llm-chat-app
```

### Git がない場合

1. GitHub のリポジトリページから「Code」→「Download ZIP」でダウンロード
2. ZIPファイルを任意の場所に展開する
3. 展開したフォルダに移動する

```bash
cd llm-chat-app
```

---

## 仮想環境の作成と有効化

仮想環境を使用することで、プロジェクト固有の依存関係を他のプロジェクトと分離できます。

### 仮想環境の作成

```bash
python -m venv .venv
```

### 仮想環境の有効化

#### Windows（コマンドプロンプト）

```cmd
.venv\Scripts\activate
```

#### Windows（PowerShell）

```powershell
.venv\Scripts\Activate.ps1
```

> 💡 PowerShell でスクリプトの実行が制限されている場合:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

### 有効化の確認

仮想環境が有効になると、プロンプトの先頭に `(.venv)` が表示されます。

```
(.venv) C:\path\to\llm-chat-app>
```

### 仮想環境の無効化

作業を終了するとき:
```bash
deactivate
```

---

## 依存関係のインストール

### ランタイム依存関係のみインストール

```bash
pip install -r requirements.txt
```

### 開発用依存関係も含めてインストール

テストやコード品質ツールも使用する場合:

```bash
pip install -e ".[dev]"
```

### インストールされるパッケージ

#### ランタイム依存関係

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| openai | >=1.0.0 | OpenAI API SDK |
| anthropic | >=0.7.0 | Anthropic Claude API SDK |
| google-generativeai | >=0.3.0 | Google Gemini API SDK |
| llama-cpp-python | >=0.2.0 | ローカルモデル実行 |
| pyyaml | >=6.0 | YAML設定ファイルの読み込み |

#### 開発用依存関係

| パッケージ | バージョン | 用途 |
|-----------|-----------|------|
| pytest | >=7.4.0 | テストフレームワーク |
| pytest-mock | >=3.12.0 | モックライブラリ |
| hypothesis | >=6.92.0 | プロパティベーステスト |
| mypy | >=1.7.0 | 型チェック |
| black | >=23.12.0 | コードフォーマッター |
| flake8 | >=7.0.0 | リンター |
| isort | >=5.13.0 | import 整理 |

### インストールの確認

```bash
pip list | findstr "openai anthropic google-generativeai llama-cpp-python pyyaml"
```

---

## 設定ファイルの作成

### config.yaml の作成

サンプルファイルをコピーして設定ファイルを作成します。

```bash
copy config.yaml.example config.yaml
```

### 設定ファイルの編集

`config.yaml` を開き、使用するモードに合わせて設定します。

#### APIモードを使用する場合

`api` セクションの `api_key` を設定します。

```yaml
api:
  provider: "openai"
  api_key: "sk-your-api-key-here"  # 実際のAPI_Keyに置き換え
  model: "gpt-3.5-turbo"
```

環境変数を使用する場合:
```yaml
api:
  provider: "openai"
  api_key: "${OPENAI_API_KEY}"
  model: "gpt-3.5-turbo"
```

API_Keyの詳細な取得方法は [docs/API_SETUP.md](API_SETUP.md) を参照してください。

#### ローカルモデルモードを使用する場合

`local` セクションの `model_path` を設定します。

```yaml
local:
  backend: "llama_cpp"
  model_path: "./models/your-model.gguf"  # ダウンロードしたモデルのパス
  n_ctx: 2048
  n_gpu_layers: 0
```

ローカルモデルの詳細なセットアップは [docs/LOCAL_MODEL_SETUP.md](LOCAL_MODEL_SETUP.md) を参照してください。

### .gitignore の確認

`config.yaml` がGitにコミットされないことを確認してください。

```bash
type .gitignore | findstr "config.yaml"
```

---

## 動作確認

### 1. インポートテスト

依存関係が正しくインストールされているか確認します。

```bash
python -c "import yaml; print('PyYAML: OK')"
python -c "import openai; print('OpenAI: OK')"
python -c "import anthropic; print('Anthropic: OK')"
python -c "import google.generativeai; print('Google GenAI: OK')"
```

### 2. テストの実行

```bash
pytest -v
```

すべてのテストがパスすれば環境構築は完了です。

### 3. アプリケーションの起動

#### APIモード

```bash
python -m llm_chat_app.main --mode api
```

#### ローカルモデルモード

```bash
python -m llm_chat_app.main --mode local
```

---

## よくある問題と対処法

### `python` コマンドが見つからない

- Python のインストール時に「Add Python to PATH」にチェックを入れたか確認する
- `python3` コマンドを試す
- コマンドプロンプトを再起動する

### `pip install` で権限エラーが出る

- 仮想環境が有効化されているか確認する（プロンプトに `(.venv)` が表示されているか）
- 管理者権限で実行する場合は `pip install --user` を使用する

### llama-cpp-python のインストールに失敗する

- [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) をインストールする
- 「C++によるデスクトップ開発」ワークロードを選択する
- 詳細は [docs/LOCAL_MODEL_SETUP.md](LOCAL_MODEL_SETUP.md) を参照

### 仮想環境の有効化ができない（PowerShell）

実行ポリシーを変更してください:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
