import * as React from "react"

import { cn } from "@/lib/utils"

// 簡易版ScrollAreaコンポーネント（Radix UIを使用せずにCSS overflowで実装）

export interface ScrollAreaProps extends React.HTMLAttributes<HTMLDivElement> {
  orientation?: "vertical" | "horizontal"
}

const ScrollArea = React.forwardRef<HTMLDivElement, ScrollAreaProps>(
  ({ className, children, orientation = "vertical", ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          "relative overflow-hidden",
          className
        )}
        {...props}
      >
        <div
          className={cn(
            "h-full w-full rounded-[inherit]",
            orientation === "vertical"
              ? "overflow-y-auto overflow-x-hidden"
              : "overflow-x-auto overflow-y-hidden"
          )}
          style={{
            scrollbarWidth: "thin",
            scrollbarColor: "hsl(var(--border)) transparent",
          }}
        >
          {children}
        </div>
      </div>
    )
  }
)
ScrollArea.displayName = "ScrollArea"

export { ScrollArea }
