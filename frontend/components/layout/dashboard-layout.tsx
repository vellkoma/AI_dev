"use client";

import { useState } from "react";
import { Menu, X } from "lucide-react";
import { cn } from "@/lib/utils";

interface DashboardLayoutProps {
  children: React.ReactNode;
  sidebar?: React.ReactNode;
}

export function DashboardLayout({ children, sidebar }: DashboardLayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div className="flex h-screen overflow-hidden">
      {/* モバイルオーバーレイ */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-20 bg-black/50 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* サイドバー */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-30 w-[280px] border-r bg-background transition-transform duration-300 lg:static lg:translate-x-0",
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-full flex-col">
          {/* サイドバーヘッダー */}
          <div className="flex h-14 items-center justify-between border-b px-4">
            <span className="text-lg font-semibold">LLM Chat</span>
            <button
              onClick={() => setSidebarOpen(false)}
              className="rounded-md p-1.5 hover:bg-accent lg:hidden"
              aria-label="サイドバーを閉じる"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* サイドバーコンテンツ */}
          <div className="flex-1 overflow-y-auto p-4">
            {sidebar ?? (
              <p className="text-sm text-muted-foreground">
                サイドバーコンテンツ
              </p>
            )}
          </div>
        </div>
      </aside>

      {/* メインコンテンツエリア */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* ヘッダー（モバイル用トグルボタン） */}
        <header className="flex h-14 items-center border-b px-4 lg:hidden">
          <button
            onClick={() => setSidebarOpen(true)}
            className="rounded-md p-1.5 hover:bg-accent"
            aria-label="サイドバーを開く"
          >
            <Menu className="h-5 w-5" />
          </button>
          <span className="ml-3 text-lg font-semibold">LLM Chat</span>
        </header>

        {/* メインコンテンツ */}
        <main className="flex-1 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
