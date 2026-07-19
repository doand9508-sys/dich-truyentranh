"use client";

import { useCallback, useRef, useState } from "react";

interface UploadZoneProps {
  onFilesAdded: (files: File[]) => void;
}

const ACCEPTED_TYPES = ["image/png", "image/jpeg", "image/webp"];

export default function UploadZone({ onFilesAdded }: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList) return;
      const files = Array.from(fileList).filter((f) =>
        ACCEPTED_TYPES.includes(f.type)
      );
      if (files.length > 0) onFilesAdded(files);
    },
    [onFilesAdded]
  );

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setIsDragging(true);
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setIsDragging(false);
        handleFiles(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
      className={`flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed p-12 text-center transition-colors cursor-pointer
        ${
          isDragging
            ? "border-indigo-500 bg-indigo-50"
            : "border-slate-300 bg-white hover:border-indigo-400 hover:bg-slate-50"
        }`}
    >
      <input
        ref={inputRef}
        type="file"
        multiple
        accept={ACCEPTED_TYPES.join(",")}
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />

      <div className="rounded-full bg-indigo-100 p-3">
        <svg
          xmlns="http://www.w3.org/2000/svg"
          className="h-7 w-7 text-indigo-600"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.8}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M12 16.5V4.5m0 0L7 9.5m5-5l5 5M4.5 19.5h15"
          />
        </svg>
      </div>

      <p className="text-sm font-medium text-slate-700">
        Drag & drop comic pages here, or{" "}
        <span className="text-indigo-600 underline">browse files</span>
      </p>
      <p className="text-xs text-slate-400">
        PNG, JPG, or WEBP — multiple pages supported, upload order is
        preserved
      </p>
    </div>
  );
}
