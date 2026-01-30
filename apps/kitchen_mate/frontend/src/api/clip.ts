import {
  Recipe,
  ClipRequest,
  ClipResponse,
  ClipUploadResponse,
  ConvertRequest,
  OutputFormat,
  ApiError,
  isAuthorizationError,
  getErrorMessage,
} from "../types/recipe";

const API_BASE = "/api";

export type AuthorizationErrorCode = "upgrade_required" | "subscription_expired";

export class ClipError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public errorCode?: AuthorizationErrorCode,
    public feature?: string
  ) {
    super(message);
    this.name = "ClipError";
  }

  get isUpgradeRequired(): boolean {
    return this.errorCode === "upgrade_required";
  }

  get isSubscriptionExpired(): boolean {
    return this.errorCode === "subscription_expired";
  }

  get isAuthorizationError(): boolean {
    return this.errorCode !== undefined;
  }
}

export async function clipRecipe(url: string, forceLlm = false): Promise<Recipe> {
  const request: ClipRequest = {
    url,
    use_llm_fallback: true,
    force_llm: forceLlm,
  };

  const response = await fetch(`${API_BASE}/clip`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
    credentials: "include",
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    if (isAuthorizationError(error.detail)) {
      throw new ClipError(
        error.detail.message,
        response.status,
        error.detail.error_code,
        error.detail.feature
      );
    }
    const message =
      typeof error.detail === "string" ? error.detail : "Failed to clip recipe";
    throw new ClipError(message, response.status);
  }

  const data: ClipResponse = await response.json();
  return data.recipe;
}

export async function uploadRecipe(file: File): Promise<ClipUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/clip/upload`, {
    method: "POST",
    body: formData,
    credentials: "include",
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    if (isAuthorizationError(error.detail)) {
      throw new ClipError(
        error.detail.message,
        response.status,
        error.detail.error_code,
        error.detail.feature
      );
    }
    const message =
      typeof error.detail === "string"
        ? error.detail
        : "Failed to upload recipe";
    throw new ClipError(message, response.status);
  }

  return response.json();
}

export async function convertRecipe(
  recipe: Recipe,
  format: Exclude<OutputFormat, "json">
): Promise<Blob> {
  const request: ConvertRequest = {
    recipe,
    format,
  };

  const response = await fetch(`${API_BASE}/convert`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
    credentials: "include",
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    const message = getErrorMessage(error.detail, "Failed to convert recipe");
    throw new ClipError(message, response.status);
  }

  return response.blob();
}

export function exportAsJson(recipe: Recipe): Blob {
  const json = JSON.stringify(recipe, null, 2);
  return new Blob([json], { type: "application/json" });
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
    case "pdf":
      return "pdf";
    case "jpeg":
      return "jpg";
    case "png":
      return "png";
    case "webp":
      return "webp";
    case "svg":
      return "svg";
  }
}
