"use client";

import { useCallback, useState } from "react";
import UploadZone from "@/components/UploadZone";
import ImageCard from "@/components/ImageCard";
import { processPage, downloadAllAsZip } from "@/lib/api";
import type { ComicPage } from "@/lib/types";

function makeClientId() {
  return `local_${Math.random().toString(36).slice(2)}_${Date.now()}`;
}

export default function Home() {
  const [pages, setPages] = useState<ComicPage[]>([]);
  const [dragClientId, setDragClientId] = useState<string | null>(null);
  const [dragOverClientId, setDragOverClientId] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);

  const updatePage = useCallback((clientId: string, patch: Partial<ComicPage>) => {
    setPages((prev) =>
      prev.map((p) => (p.clientId === clientId ? { ...p, ...patch } : p))
    );
  }, []);

  // --- Upload & queue -----------------------------------------------------
  const handleFilesAdded = useCallback(
    (files: File[]) => {
      setPages((prev) => {
        const startOrder = prev.length;
        const newPages: ComicPage[] = files.map((file, i) => ({
          clientId: makeClientId(),
          order: startOrder + i,
          file,
          previewUrl: URL.createObjectURL(file),
          step: "queued",
        }));
        return [...prev, ...newPages];
      });
    },
    []
  );

  // --- Reordering (native HTML5 drag & drop) -------------------------------
  const handleDrop = useCallback(
    (targetClientId: string) => {
      if (!dragClientId || dragClientId === targetClientId) {
        setDragOverClientId(null);
        return;
      }
      setPages((prev) => {
        const list = [...prev];
        const fromIdx = list.findIndex((p) => p.clientId === dragClientId);
        const toIdx = list.findIndex((p) => p.clientId === targetClientId);
        if (fromIdx === -1 || toIdx === -1) return prev;

        const [moved] = list.splice(fromIdx, 1);
        list.splice(toIdx, 0, moved);
        return list.map((p, i) => ({ ...p, order: i }));
      });
      setDragClientId(null);
      setDragOverClientId(null);
    },
    [dragClientId]
  );

  // --- Run the full pipeline for every queued page -------------------------
  const handleTranslateAll = useCallback(async () => {
    setIsRunning(true);

    // Process sequentially to keep LLM/API load predictable; swap for
    // Promise.all-with-concurrency-limit if you want parallel throughput.
    for (const page of pages) {
      if (page.step === "done") continue;
      try {
        const result = await processPage(page.file, page.order, (step) =>
          updatePage(page.clientId, { step })
        );
        updatePage(page.clientId, {
          step: "done",
          imageId: result.imageId,
          originalUrl: result.originalUrl,
          finalUrl: result.finalUrl,
          boxes: result.boxes,
          translations: result.translations,
        });
      } catch (err) {
        updatePage(page.clientId, {
          step: "error",
          errorMessage: err instanceof Error ? err.message : "Unknown error",
        });
      }
    }

    setIsRunning(false);
  }, [pages, updatePage]);

  const handleDownloadAll = useCallback(async () => {
    try {
      await downloadAllAsZip();
    } catch (err) {
      alert(err instanceof Error ? err.message : "Download failed");
    }
  }, []);

  const orderedPages = [...pages].sort((a, b) => a.order - b.order);
  const allDone = pages.length > 0 && pages.every((p) => p.step === "done");
  const anyDone = pages.some((p) => p.step === "done");

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <header className="mb-8 flex flex-col gap-1.5">
        <h1 className="text-2xl font-bold text-slate-900">Comic Translator</h1>
        <p className="text-sm text-slate-500">
          Upload comic/manga pages, auto-translate to Vietnamese, and
          download the localized set.
        </p>
      </header>

      <UploadZone onFilesAdded={handleFilesAdded} />

      {pages.length > 0 && (
        <>
          <div className="mt-8 flex items-center justify-between">
            <h2 className="text-sm font-semibold text-slate-700">
              {pages.length} page{pages.length > 1 ? "s" : ""} — drag to
              reorder
            </h2>

            <div className="flex gap-2">
              <button
                onClick={handleTranslateAll}
                disabled={isRunning}
                className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {isRunning ? "Processing…" : "Translate All"}
              </button>
              <button
                onClick={handleDownloadAll}
                disabled={!anyDone}
                className="rounded-lg border border-slate-300 bg-white px-4 py-2 text-sm font-medium text-slate-700 shadow-sm transition-colors hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Download All (ZIP)
              </button>
            </div>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5">
            {orderedPages.map((page, index) => (
              <ImageCard
                key={page.clientId}
                page={page}
                index={index}
                onDragStart={setDragClientId}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOverClientId(page.clientId);
                }}
                onDrop={handleDrop}
                isDragTarget={dragOverClientId === page.clientId}
              />
            ))}
          </div>

          {allDone && (
            <p className="mt-6 text-center text-sm text-emerald-600">
              All pages translated — ready to download.
            </p>
          )}
        </>
      )}
    </main>
  );
}
