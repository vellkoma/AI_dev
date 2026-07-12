# ローカルモデル セットアップガイド

本ドキュメントでは、オープンソースLLMモデルをローカル環境で実行するためのセットアップ手順を説明します。

## 目次

1. [システム要件](#システム要件)
2. [llama-cpp-python のインストール](#llama-cpp-python-のインストール)
3. [GGUFモデルのダウンロード](#ggufモデルのダウンロード)
4. [推奨モデル](#推奨モデル)
5. [Ollama のインストールと設定（オプション）](#ollama-のインストールと設定オプション)
6. [config.yaml への設定方法](#configyaml-への設定方法)
7. [トラブルシューティング](#トラブルシューティング)

---

## システム要件

### 最小要件

| 項目 | 要件 |
|------|------|
| OS | Windows 10/11 (64-bit) |
| RAM | 8GB 以上 |
| ストレージ | 10GB 以上の空き容量（モデルサイズに依存） |
| CPU | 64-bit対応プロセッサ |
| Python | 3.9 以上 |

### 推奨要件

| 項目 | 要件 |
|------|------|
| RAM | 16GB 以上 |
| ストレージ | SSD 20GB 以上 |
| GPU | NVIDIA GPU（VRAM 4GB以上、CUDA対応）※オプション |

### メモリ使用量の目安

| モデルサイズ | 量子化 | 必要RAM |
|-------------|--------|---------|
| 7B パラメータ | Q4_K_M | 約 4-5GB |
| 7B パラメータ | Q5_K_M | 約 5-6GB |
| 13B パラメータ | Q4_K_M | 約 8-9GB |
| 13B パラメータ | Q5_K_M | 約 10-11GB |

> 💡 **推奨**: 初めての方は **7Bパラメータ、Q4_K_M量子化** のモデルをお勧めします。

---

## llama-cpp-python のインストール

### CPU版のインストール（推奨・簡単）

```bash
pip install llama-cpp-python
```

### GPU版のインストール（NVIDIA CUDA対応）

GPU版を使用するとモデルの推論が高速になります。

#### 前提条件

- NVIDIA GPU（CUDA対応）
- [CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit) がインストール済み
- [cuDNN](https://developer.nvidia.com/cudnn) がインストール済み

#### インストールコマンド

```bash
# Windows（CUDA対応ビルド）
set CMAKE_ARGS=-DGGML_CUDA=on
pip install llama-cpp-python --force-reinstall --no-cache-dir
```

#### CUDA のバージョン確認

```bash
nvcc --version
```

> ⚠️ **注意**: GPU版のインストールにはC++コンパイラ（Visual Studio Build Tools）が必要です。

### インストールの確認

```python
python -c "from llama_cpp import Llama; print('llama-cpp-python が正常にインストールされています')"
```

---

## GGUFモデルのダウンロード

### GGUF形式について

GGUF（GPT-Generated Unified Format）は llama.cpp で使用されるモデル形式です。量子化されたモデルはファイルサイズが小さく、少ないメモリで実行できます。

### HuggingFace からのダウンロード

1. [HuggingFace](https://huggingface.co/models?library=gguf) にアクセスする
2. 使いたいモデルを検索する
3. 「Files and versions」タブで `.gguf` ファイルを探す
4. ダウンロードボタンをクリック、または以下のコマンドを使用する

```bash
# 例: Llama 2 7B Chat モデルのダウンロード
# ブラウザからダウンロードするか、以下のように curl を使用
curl -L -o models/llama-2-7b-chat.Q4_K_M.gguf "https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF/resolve/main/llama-2-7b-chat.Q4_K_M.gguf"
```

### ダウンロード先

モデルファイルはプロジェクトの `models/` ディレクトリに配置してください。

```
llm-chat-app/
└── models/
    └── llama-2-7b-chat.Q4_K_M.gguf  ← ここに配置
```

---

## 推奨モデル

初めての方に推奨する 7Bパラメータのモデルです。

### Llama 2 7B Chat

| 項目 | 詳細 |
|------|------|
| HuggingFace | [TheBloke/Llama-2-7B-Chat-GGUF](https://huggingface.co/TheBloke/Llama-2-7B-Chat-GGUF) |
| 推奨ファイル | `llama-2-7b-chat.Q4_K_M.gguf` |
| ファイルサイズ | 約 4.1GB |
| 必要RAM | 約 5GB |
| 特徴 | Meta社製、チャット向けファインチューニング済み |

### Qwen2 7B Instruct

| 項目 | 詳細 |
|------|------|
| HuggingFace | [Qwen/Qwen2-7B-Instruct-GGUF](https://huggingface.co/Qwen/Qwen2-7B-Instruct-GGUF) |
| 推奨ファイル | `qwen2-7b-instruct-q4_k_m.gguf` |
| ファイルサイズ | 約 4.4GB |
| 必要RAM | 約 5GB |
| 特徴 | Alibaba社製、日本語性能が比較的良好 |

### Gemma 2 9B Instruct

| 項目 | 詳細 |
|------|------|
| HuggingFace | [bartowski/gemma-2-9b-it-GGUF](https://huggingface.co/bartowski/gemma-2-9b-it-GGUF) |
| 推奨ファイル | `gemma-2-9b-it-Q4_K_M.gguf` |
| ファイルサイズ | 約 5.8GB |
| 必要RAM | 約 7GB |
| 特徴 | Google社製、高品質な応答 |

### 量子化レベルの選び方

| 量子化 | 品質 | サイズ | 速度 | 推奨 |
|--------|------|--------|------|------|
| Q4_K_M | 良好 | 小 | 速い | ⭐ 初心者向け |
| Q5_K_M | 高い | 中 | 普通 | バランス重視 |
| Q6_K | 非常に高い | 大 | やや遅い | 品質重視 |
| Q8_0 | 最高 | 最大 | 遅い | メモリに余裕がある場合 |

---

## Ollama のインストールと設定（オプション）

Ollamaはローカルモデルの管理・実行を簡単にするツールです。llama-cpp-pythonの代替として使用できます。

### インストール手順

1. [Ollama 公式サイト](https://ollama.ai/) にアクセスする
2. Windows版をダウンロードしてインストールする
3. インストール完了後、コマンドプロンプトで確認する

```bash
ollama --version
```

### モデルのダウンロード

```bash
# Llama 2 をダウンロード
ollama pull llama2

# Qwen2 をダウンロード
ollama pull qwen2

# Gemma 2 をダウンロード
ollama pull gemma2
```

### 動作確認

```bash
# Ollama でチャット（テスト）
ollama run llama2 "こんにちは"
```

### config.yaml への設定

```yaml
local:
  backend: "ollama"
  model_path: "llama2"   # Ollamaのモデル名を指定
  n_ctx: 2048
  n_gpu_layers: 0
```

---

## config.yaml への設定方法

### llama-cpp-python を使用する場合

```yaml
local:
  # バックエンド: llama_cpp
  backend: "llama_cpp"

  # モデルファイルのパス（.gguf形式）
  model_path: "./models/llama-2-7b-chat.Q4_K_M.gguf"

  # コンテキストウィンドウサイズ（トークン数）
  # 大きいほど長い会話に対応できるが、メモリ使用量が増加
  n_ctx: 2048

  # GPU使用レイヤー数
  # 0 = CPUのみ
  # -1 = 全レイヤーをGPUで実行
  # 1-99 = 指定数のレイヤーをGPUにオフロード
  n_gpu_layers: 0
```

### Ollama を使用する場合

```yaml
local:
  backend: "ollama"
  model_path: "llama2"
  n_ctx: 2048
  n_gpu_layers: 0
```

### 共通設定の調整

```yaml
common:
  # 温度パラメータ（0.0-2.0）
  # 低い = 決定的な応答、高い = 創造的な応答
  temperature: 0.7

  # 最大生成トークン数
  # ローカルモデルでは低めに設定すると応答が速い
  max_tokens: 1000

  # 会話履歴の最大トークン数
  history_max_tokens: 2000
```

---

## トラブルシューティング

### モデルファイルが見つからない

```
エラー: モデルファイルが見つかりません
```

**対処法**:
1. `config.yaml` の `model_path` が正しいか確認する
2. モデルファイルが `models/` ディレクトリに存在するか確認する
3. ファイル名（大文字・小文字）が正確か確認する

### メモリ不足エラー

```
エラー: メモリ不足によりモデルのロードに失敗しました
```

**対処法**:
1. より小さいモデル（7Bパラメータ、Q4_K_M量子化）を使用する
2. `n_ctx` の値を小さくする（512〜1024）
3. 他のアプリケーションを終了してメモリを確保する
4. タスクマネージャーでメモリ使用状況を確認する

### GPU が認識されない

```
エラー: CUDA が利用できません
```

**対処法**:
1. NVIDIA ドライバが最新か確認する
2. CUDA Toolkit がインストールされているか確認する
3. `n_gpu_layers: 0` に設定してCPUモードで動作させる

### llama-cpp-python のインストールに失敗する

**対処法**:
1. Visual Studio Build Tools がインストールされているか確認する
2. Python のバージョンが 3.9 以上か確認する
3. 以下のコマンドで再インストールを試す:

```bash
pip install llama-cpp-python --force-reinstall --no-cache-dir
```

### 応答が非常に遅い

**対処法**:
1. `max_tokens` の値を小さくする（500〜1000）
2. `n_ctx` の値を小さくする（1024〜2048）
3. GPU版をインストールして `n_gpu_layers` を設定する
4. より小さい量子化レベル（Q4_K_M）のモデルを使用する
