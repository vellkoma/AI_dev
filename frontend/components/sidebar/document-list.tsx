"use client";

import { useEffect, useRef, useState } from "react";
import { FileText, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useToast } from "@/components/ui/use-toast";
import { api } from "@/lib/api";
import type { DocumentInfo } from "@/types";

// ファイルサイズを読みやすい形式にフォーマット
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function DocumentList() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [uploading, setUploading] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { toast } = useToast();

  // ドキュメント一覧を取得
  const fetchDocuments = () => {
    api.rag
      .list()
      .then((data: { documents: DocumentInfo[] }) => {
        setDocuments(data.documents ?? []);
      })
      .catch(() => {
        setDocuments([]);
      });
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  // ファイルアップロードハンドラー
  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      const result = await api.rag.upload(file);
      if (result.success && result.document) {
        toast({
          title: "アップロード完了",
          description: `${file.name} を追加しました（${result.document.chunk_count} チャンク）`,
        });
        fetchDocuments();
      } else {
        toast({
          title: "アップロード失敗",
          description: result.message || "ファイルの処理に失敗しました",
          variant: "destructive",
        });
      }
    } catch {
      toast({
        title: "アップロードエラー",
        description: "サーバーとの通信に失敗しました",
        variant: "destructive",
      });
    } finally {
      setUploading(false);
      // ファイル入力をリセット
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  // ドキュメント削除ハンドラー
  const handleDelete = async (doc: DocumentInfo) => {
    const confirmed = window.confirm(
      `「${doc.filename}」を削除しますか？\n関連するチャンクとベクトルも削除されます。`
    );
    if (!confirmed) return;

    setDeletingId(doc.document_id);
    try {
      await api.rag.delete(doc.document_id);
      toast({
        title: "削除完了",
        description: `${doc.filename} を削除しました`,
      });
      fetchDocuments();
    } catch {
      toast({
        title: "削除エラー",
        description: "ドキュメントの削除に失敗しました",
        variant: "destructive",
      });
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="flex items-center gap-2 text-sm font-medium">
          <FileText className="h-4 w-4" />
          ドキュメント
        </label>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
          aria-label="ドキュメントを追加"
        >
          <Plus className="h-4 w-4" />
        </Button>
      </div>

      {/* 非表示のファイル入力 */}
      <input
        ref={fileInputRef}
        type="file"
        accept=".pdf,.txt,.md,.markdown,text/plain,text/markdown,application/pdf"
        onChange={handleUpload}
        className="hidden"
        aria-hidden="true"
      />

      {/* アップロード中インジケーター */}
      {uploading && (
        <p className="text-xs text-muted-foreground animate-pulse">
          アップロード中...
        </p>
      )}

      {/* ドキュメント一覧 */}
      {documents.length === 0 ? (
        <p className="text-xs text-muted-foreground">
          ドキュメントがありません
        </p>
      ) : (
        <ul className="space-y-2">
          {documents.map((doc) => (
            <li
              key={doc.document_id}
              className="flex items-start justify-between gap-2 rounded-md border p-2 text-xs"
            >
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium" title={doc.filename}>
                  {doc.filename}
                </p>
                <p className="text-muted-foreground">
                  {doc.chunk_count} チャンク · {formatFileSize(doc.file_size)}
                </p>
              </div>
              <Button
                variant="ghost"
                size="sm"
                className="h-6 w-6 shrink-0 p-0 text-destructive hover:text-destructive"
                onClick={() => handleDelete(doc)}
                disabled={deletingId === doc.document_id}
                aria-label={`${doc.filename} を削除`}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </Button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
