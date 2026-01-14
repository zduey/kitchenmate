import { Recipe, ClipRequest, ConvertRequest, OutputFormat, ApiError, ClipStreamEvent } from "../types/recipe";

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
    use_llm_fallback: true,
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

export async function clipRecipeWithProgress(
  url: string,
  onProgress: (event: ClipStreamEvent) => void
): Promise<Recipe> {
  const request: ClipRequest = {
    url,
    use_llm_fallback: true,
    stream: true,
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

  const reader = response.body?.getReader();
  if (!reader) {
    throw new ClipError("Failed to read response stream", 500);
  }

  const decoder = new TextDecoder();
  let buffer = "";
  let recipe: Recipe | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // Parse SSE events from buffer
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = JSON.parse(line.slice(6)) as ClipStreamEvent;
        onProgress(data);

        if (data.stage === "complete") {
          recipe = data.recipe;
        } else if (data.stage === "error") {
          throw new ClipError(data.message, data.status);
        }
      }
    }
  }

  if (!recipe) {
    throw new ClipError("No recipe received from stream", 500);
  }

  return recipe;
}

export async function convertRecipe(
  recipe: Recipe,
  format: "text" | "markdown"
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
  });

  if (!response.ok) {
    const error: ApiError = await response.json();
    throw new ClipError(error.detail, response.status);
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
  }
}
