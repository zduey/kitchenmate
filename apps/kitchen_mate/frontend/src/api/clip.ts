import { Recipe, ClipRequest, OutputFormat, ApiError } from "../types/recipe";

const API_BASE = "/api";

export class ClipError extends Error {
  constructor(
    message: string,
    public statusCode: number
  ) {
    super(message);
    this.name = "ClipError";
  }
}

export async function clipRecipe(url: string): Promise<Recipe> {
  const request: ClipRequest = {
    url,
    format: "json",
  };

  const response = await fetch(`${API_BASE}/clip`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new ClipError(error.detail, response.status);
  }

  return response.json();
}

export async function downloadRecipe(
  url: string,
  format: OutputFormat
): Promise<Blob> {
  const request: ClipRequest = {
    url,
    format,
    download: true,
  };

  const response = await fetch(`${API_BASE}/clip`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new ClipError(error.detail, response.status);
  }

  return response.blob();
}

export function triggerDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function getFileExtension(format: OutputFormat): string {
  switch (format) {
    case "json":
      return "json";
    case "text":
      return "txt";
    case "markdown":
      return "md";
  }
}
