"use client";

import { useState } from "react";
import type { ComicPage, PipelineStep } from "@/lib/types";

interface ImageCardProps {
  page: ComicPage;
  index: number; // 0-based position in the current order
  onDragStart: (clientId: string) => void;
  onDragOver: (e: React.DragEvent) => void;
  onDrop: (clientId: string) => void;
  isDragTarget: boolean;
}

const STEP_LABELS: Record<PipelineStep, string> = {
  queued: "Queued",
  uploading: "Uploading",
  detecting: "Detecting Text",
  translating: "Translating",
  rendering: "Rendering",
  done: "Done",
  error: "Failed",
};

// Rough progress percentage per step, purely for the visual bar.
const STEP_PROGRESS: Record<PipelineStep, number> = {
  queued: 0,
  uploading: 15,
  detecting: 40,
  translating: 65,
  rendering: 88,
  done: 100,
  error: 100,
};

export default function ImageCard({
  page,
  index,
  onDragStart,
  onDragOver,
  onDrop,
  isDragTarget,
}: ImageCardProps) {
  const [showAfter, setShowAfter] = useState(true);
  const isProcessing = !["queued", "done", "error"].includes(page.step);

  return (
    <div
      draggable
      onDragStart={() => onDragStart(page.clientId)}
      onDragOver={onDragOver}
      onDrop={() => onDrop(page.clientId)}
      className={`group relative flex flex-col overflow-hidden rounded-xl border bg-white shadow-sm transition-all
        ${isDragTarget ? "border-indigo-500 ring-2 ring-indigo-300" : "border-slate-200"}
        cursor-grab active:cursor-grabbing`}
    >
      {/* Order badge */}
      <div className="absolute left-2 top-2 z-10 flex h-7 w-7 items-center justify-center rounded-full bg-slate-900/80 text-xs font-semibold text-white">
        {index + 1}
      </div>

      {/* Before/After toggle, only once we have a rendered result */}
      {page.finalUrl && (
        <button
          onClick={() => setShowAfter((s) => !s)}
          className="absolute right-2 top-2 z-10 rounded-full bg-white/90 px-2.5 py-1 text-[11px] font-medium text-slate-700 shadow hover:bg-white"
        >
          {showAfter ? "After" : "Before"}
        </button>
      )}

      {/* Image */}
      <div className="relative aspect-[3/4] w-full bg-slate-100">
        <img
          src={showAfter && page.finalUrl ? page.finalUrl : page.previewUrl}
          alt={`Page ${index + 1}`}
          className="h-full w-full object-cover"
        />

        {isProcessing && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-900/40 backdrop-blur-[1px]">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-white border-t-transparent" />
          </div>
        )}
      </div>

      {/* Status / progress bar */}
      <div className="flex flex-col gap-1.5 p-3">
        <div className="flex items-center justify-between text-xs">
          <span
            className={`font-medium ${
              page.step === "error" ? "text-red-600" : "text-slate-600"
            }`}
          >
            {STEP_LABELS[page.step]}
          </span>
          {page.step === "done" && (
            <span className="text-emerald-600">✓</span>
          )}
        </div>

        <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              page.step === "error" ? "bg-red-500" : "bg-indigo-500"
            }`}
            style={{ width: `${STEP_PROGRESS[page.step]}%` }}
          />
        </div>

        {page.step === "error" && page.errorMessage && (
          <p className="truncate text-[11px] text-red-500" title={page.errorMessage}>
            {page.errorMessage}
          </p>
        )}
      </div>
    </div>
  );
}
