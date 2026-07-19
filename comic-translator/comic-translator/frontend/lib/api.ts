import type { BoundingBox, TranslatedBox } from "./types";

// Configure via .env.local: NEXT_PUBLIC_API_URL=http://localhost:8000
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(detail);
  }
  return res.json() as Promise<T>;
}

export interface UploadResponse {
  image_id: string;
  original_url: string;
  order: number;
  width: number;
  height: number;
}

export interface DetectResponse {
  image_id: string;
  width: number;
  height: number;
  boxes: BoundingBox[];
}

export interface TranslateResponse {
  image_id: string;
  translations: TranslatedBox[];
}

export interface RenderResponse {
  image_id: string;
  final_image_url: string;
}

/** Step 0: upload a single page image with its order index. */
export async function uploadImage(
  file: File,
  order: number
): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("order", String(order));

  const res = await fetch(`${API_BASE_URL}/api/upload`, {
    method: "POST",
    body: form,
  });
  return handleResponse<UploadResponse>(res);
}

/** Step 1: run text detection on an already-uploaded page. */
export async function detectText(imageId: string): Promise<DetectResponse> {
  const res = await fetch(`${API_BASE_URL}/api/detect/${imageId}`, {
    method: "POST",
  });
  return handleResponse<DetectResponse>(res);
}

/** Step 2: translate all detected boxes for a page via the LLM. */
export async function translateBoxes(
  imageId: string,
  boxes: BoundingBox[]
): Promise<TranslateResponse> {
  const res = await fetch(`${API_BASE_URL}/api/translate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_id: imageId, boxes }),
  });
  return handleResponse<TranslateResponse>(res);
}

/** Step 3: inpaint + typeset -> final rendered page. */
export async function renderPage(
  imageId: string,
  boxes: BoundingBox[],
  translations: TranslatedBox[]
): Promise<RenderResponse> {
  const res = await fetch(`${API_BASE_URL}/api/render/${imageId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_id: imageId, boxes, translations }),
  });
  return handleResponse<RenderResponse>(res);
}

/** Runs the full per-page pipeline sequentially, reporting progress via callback. */
export async function processPage(
  file: File,
  order: number,
  onStep: (step: "uploading" | "detecting" | "translating" | "rendering") => void
) {
  onStep("uploading");
  const uploaded = await uploadImage(file, order);

  onStep("detecting");
  const detected = await detectText(uploaded.image_id);

  onStep("translating");
  const translated = await translateBoxes(uploaded.image_id, detected.boxes);

  onStep("rendering");
  const rendered = await renderPage(
    uploaded.image_id,
    detected.boxes,
    translated.translations
  );

  return {
    imageId: uploaded.image_id,
    originalUrl: `${API_BASE_URL}${uploaded.original_url}`,
    finalUrl: `${API_BASE_URL}${rendered.final_image_url}`,
    boxes: detected.boxes,
    translations: translated.translations,
  };
}

/** Triggers a browser download of the ZIP containing all rendered pages. */
export async function downloadAllAsZip(): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/download-all`);
  if (!res.ok) throw new Error("Failed to build ZIP");

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "comic_translated.zip";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
