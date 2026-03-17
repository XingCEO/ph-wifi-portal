"use client";

import { useEffect, useState } from "react";
import { CheckCircle, XCircle, X } from "lucide-react";

export type ToastType = "success" | "error";

interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

let toastId = 0;
let setToastsExternal: ((fn: (prev: Toast[]) => Toast[]) => void) | null = null;

export function toast(type: ToastType, message: string) {
  if (setToastsExternal) {
    const id = ++toastId;
    setToastsExternal((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToastsExternal!((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  }
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    setToastsExternal = setToasts;
    return () => { setToastsExternal = null; };
  }, []);

  return (
    <div className="fixed bottom-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg border pointer-events-auto
            backdrop-blur-xl text-sm font-medium max-w-sm
            ${t.type === "success"
              ? "bg-white/80 border-green-200 text-green-800"
              : "bg-white/80 border-red-200 text-red-700"
            }`}
        >
          {t.type === "success"
            ? <CheckCircle size={18} className="text-green-600 shrink-0" />
            : <XCircle size={18} className="text-red-500 shrink-0" />
          }
          <span className="flex-1">{t.message}</span>
          <button
            onClick={() => setToasts((prev) => prev.filter((x) => x.id !== t.id))}
            className="text-gray-400 hover:text-gray-600 shrink-0"
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
