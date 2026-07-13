"use client"

import { useToast } from "@/components/ui/use-toast"
import { Toast, ToastTitle, ToastDescription } from "@/components/ui/toast"

export function Toaster() {
  const { toasts, dismiss } = useToast()

  return (
    <div className="fixed bottom-0 right-0 z-[100] flex max-h-screen w-full flex-col-reverse p-4 sm:bottom-0 sm:right-0 sm:top-auto sm:flex-col-reverse md:max-w-[420px]">
      {toasts.map((t) => (
        <div key={t.id} className="mb-2">
          <Toast variant={t.variant} onClose={() => dismiss(t.id)}>
            <div className="grid gap-1">
              {t.title && <ToastTitle>{t.title}</ToastTitle>}
              {t.description && (
                <ToastDescription>{t.description}</ToastDescription>
              )}
            </div>
          </Toast>
        </div>
      ))}
    </div>
  )
}
