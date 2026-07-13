"use client";

import { useState, useEffect, useCallback } from "react";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";

interface SessionSearchProps {
  onSearch: (keyword: string) => void;
}

/**
 * セッション検索入力コンポーネント
 * デバウンス付きキーワード検索を提供する
 */
export function SessionSearch({ onSearch }: SessionSearchProps) {
  const [query, setQuery] = useState("");

  // デバウンス処理（300ms）
  useEffect(() => {
    const timer = setTimeout(() => {
      onSearch(query);
    }, 300);
    return () => clearTimeout(timer);
  }, [query, onSearch]);

  return (
    <div className="relative">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
      <Input
        placeholder="会話を検索..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="pl-9"
      />
    </div>
  );
}
