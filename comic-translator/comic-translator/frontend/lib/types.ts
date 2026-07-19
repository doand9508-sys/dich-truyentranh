export type PipelineStep =
  | "queued"
  | "uploading"
  | "detecting"
  | "translating"
  | "rendering"
  | "done"
  | "error";

export interface BoundingBox {
  id: string;
  x: number;
  y: number;
  w: number;
  h: number;
  original_text: string;
}

export interface TranslatedBox {
  id: string;
  translated_text: string;
}

/** Client-side state for a single page, from file drop through to final render. */
export interface ComicPage {
  /** Stable client-side key (before we have a server image_id). */
  clientId: string;
  /** Server-assigned id, available after upload completes. */
  imageId?: string;
  order: number;
  file: File;
  previewUrl: string; // local object URL for the original thumbnail
  originalUrl?: string; // server-served original
  finalUrl?: string; // server-served rendered result
  boxes?: BoundingBox[];
  translations?: TranslatedBox[];
  step: PipelineStep;
  errorMessage?: string;
}
